# DanceSync — Build Plan

The alignment spike validated the approach, and the MVP (Phases 1–4) is built: upload a song and a practice video, align them, confirm the match when it's ambiguous, and watch or download the synced result. What's left is Phase 5 (polish and deployment) and the post-MVP features. Each feature is specced in [`specs/`](specs/) so it can be handed to Claude Code as a self-contained task, and each spec is broken into day-sized tickets in [`tickets/`](tickets/). **This file holds status and rationale; [`tickets/README.md`](tickets/README.md) holds the working order.**

**Audience:** the owner and friends, running DanceSync locally or self-hosted rather than as a public site. That shapes Phase 5, which needs basic access control but nothing for multiple tenants, and it's what makes YouTube import viable.

---

## Product concept

A dancer practices to music played at reduced speed (typically 0.75x) on a laptop speaker, filming themselves on their phone. DanceSync takes that recording and finds where in the song it starts and how fast the song was playing. It then re-times the video to the original speed, so the dancer can review the practice at full tempo, in sync with the reference track, next to the original choreography.

### User flow (as built)

1. **Song:** pick a song used before, or upload a new one (an audio file, or a video of the choreography).
2. **Video:** upload the practice video. The server aligns it, which takes 10–30 s.
3. **Match:** this step appears only when the match is ambiguous (a repeated chorus, `peak_ratio` < 1.2). It shows the top 3 candidates on a song timeline and plays 8 s of the song at each one, and the user picks the right one.
4. **Watch:** the synced take plays next to the reference video, with one play bar for both. The sound can be the song or the room (the phone's own recording). The user can slow the review to 0.5× or 0.75×, pick a layout (side by side, stacked, or take only), and download exactly what's on screen.

---

## Status

| Phase | Status |
|---|---|
| 1. Production matcher | Done |
| 2. Backend API | Done |
| 3. Video sync engine | Done |
| 4. Web UI | Done |
| 5. Polish & deploy | Not started; the items marked **MVP** are what's left before the MVP is done |
| Post-MVP features | Specced in [`specs/`](specs/) |

Invariant 7 (render cache names) is enforced by one `RenderParams` record shared by the server's cache id and the browser's URL, with a test that fails if they drift (DS-03).

pytest covers the Tier A matcher regression, the ambiguity threshold, the API routes, and real ffmpeg renders. Vitest covers the UI's pure helpers in `web/src/flow.js`.

---

## Phases 1–4: what was built

Where the build departed from the original plan, the difference is noted here. The code is the source of truth, not this file.

### Phase 1 — Production matcher (`dancesync/`)

Built as planned: chroma CQT features, overlap-normalized sliding correlation, and a rate search over `RATES = (1.0, 0.75, 0.5)`. `MatchResult` carries the top-N candidates, and every offset is in the original timeline. Stretched reference features are cached by content hash. The Tier A cases are the pytest regression suite.

- **Added:** `AMBIGUOUS_PEAK_RATIO = 1.2`, set from measurements. A chorus repeated word for word scores 1.04–1.06, and passages heard once score 1.15–2.0. `tests/test_ambiguity.py` guards the threshold.

### Phase 2 — Backend API (`server/`)

Built as planned: FastAPI, local storage keyed by content hash, alignment done synchronously inside the POST, and upload limits of 100 MB for songs and 500 MB for clips.

- **Metadata** lives in a catalog of JSON files (`server/catalog.py`), kept apart from the raw file bytes (`server/storage.py`) so that either one can be replaced on its own.
- **`AlignmentResult.ambiguous`** is decided once, at upload. `peak_ratio` is `null` in JSON when no other peak competes; that's how the matcher's infinity comes through.
- **`GET /api/references/{id}/media`** serves the song file, with range requests, for the match previews and the side-by-side player.
- **References are listed newest first.**

Endpoints:
- `POST /api/references`, `GET /api/references`, `GET /api/references/{id}/media`
- `POST /api/clips`, `GET /api/clips/{id}`, `GET /api/clips/{id}/media` (the uploaded take, with range requests; for instant preview), `POST /api/clips/{id}/select`, `PUT|DELETE /api/clips/{id}/manual` (an alignment set by hand; post-MVP)
- `GET|HEAD /api/clips/{id}/synced?sound=song|room&layout=take|side-by-side|stacked`

### Phase 3 — Video sync engine (`dancesync/sync.py`, `dancesync/ffmpeg.py`)

Built as planned: one ffmpeg command per render, `setpts=PTS*rate`, and the reference cut at `offset_sec`, preceded by silence when the offset is negative. Output is H.264 baseline at CRF 18 with AAC audio.

- **Every captured frame is kept** (`-fps_mode passthrough`). A 30 fps take at 0.75x comes out at 40 fps instead of losing frames.
- **Two sounds:** `song` (the reference track) or `room` (the phone's own recording, sped up with `atempo`).
- **Three layouts:** `take` alone, `side-by-side` (reference on the left, both 720 px high), or `stacked` (reference on top, both 720 px wide; added post-MVP). The last two are one `build_compare_command` on a 60 fps grid.
- **Renders are cached** under a filename that encodes every input. Each one is written to a temp file and then renamed, so a failed render never looks finished.
- **`HEAD` on `/synced` renders without sending a body.** The UI waits on it because iOS Safari doesn't fetch a `<video>` source until the user presses play.

### Phase 4 — Web UI (`web/`)

Built with React 19, Vite, and plain CSS, and no other runtime dependencies. Vite proxies `/api`, so the browser only ever talks to one origin.

- **Step flow:** Song → Video → Match (only when ambiguous) → Watch.
- **Match screen:** changed from the plan. A song timeline with candidate markers and 8 s audio previews replaced the score-curve plot and video thumbnails.
- **Watch screen:**
  - The take and the reference share one play bar. The take sets the time, and the reference follows it by nudging its `playbackRate` (`useLinkedPlayback.js`).
  - The screen also has the Song/Room toggle and the download buttons.
- **Pure helpers** live in `web/src/flow.js`, with Vitest tests.

---

## Phase 5 — Polish & deploy

Ticketed as three separate tracks — Ship (what's left before the MVP is done), Operate, and Platform. See [`tickets/README.md`](tickets/README.md).

- **Tests in CI (MVP):** done. `.github/workflows/test.yml` runs `pytest` and `npm --prefix web test` on every PR.
- **Error cases (MVP):** friendly messages already exist for files that are too big, unsupported file types, and an unreachable server. Still needed:
  - ~~clips too short to match~~ (done: `MIN_CLIP_SEC` = 10 s, measured; the upload answers 422 with the clip's length)
  - ~~no strong peak anywhere~~ (done: `MIN_MATCH_SCORE` = 3.5, measured; `AlignmentResult.failed` and a "couldn't find this take" screen with a "watch anyway" escape). Handing off to manual placement ([manual-alignment](specs/manual-alignment.md)) is DS-26.
  - ~~a startup check that stops the server if ffmpeg is missing~~ (done)
- **One-command run (MVP):** done. A multi-stage `Dockerfile` (Node builds `web/dist`, Python 3.11 slim with ffmpeg runs it), FastAPI serving that build from the API's origin (`server/web.py`), and `docker compose up` with named volumes for data and cache. Settings come from `DANCESYNC_*` env vars (`.env.example`).
- **Access control:** done. Set `DANCESYNC_PASSPHRASE` and every `/api` request needs the cookie from `POST /api/session`; the web app shows a sign-in screen. Unset means no sign-in, as before.
- **Render cleanup:** done. Renders are capped at `DANCESYNC_RENDER_CACHE_GB` (5 GB by default); after each new render, the least recently served ones are deleted (`server/render_cache.py`) and re-rendered on demand.
- **Background jobs and progress:** move alignment and rendering to a job queue that reports progress over server-sent events (SSE). Needed for:
  - [follow-dancer](specs/follow-dancer.md), where tracking takes minutes
  - any reverse proxy with a 60 s timeout in front of a long render
- **Hosting:** runbook in [`docs/hosting.md`](docs/hosting.md): a small VPS with Docker and Caddy (600 s proxy timeouts, from measured render times), or a home machine over Tailscale. The YouTube-from-this-host test waits until YouTube import exists.
- **Benchmark harness:** real-world clips with known correct offsets, run in CI to catch matcher regressions.
- **Deferred: cloud storage (S3/GCS).** A self-hosted deployment for the owner and friends doesn't need it. `server/storage.py` stays separate so it can be swapped in later.

---

## Post-MVP features

These come from `TODO.md`, and each one has its own spec. Recommended order:

| # | Feature | Spec | Size | Depends on |
|---|---|---|---|---|
| 1 | Instant preview (watch before rendering) — **partly done**: the player leads from the sound-making element and re-times one room render live (DS-17, and DS-18's timing); playing the raw clip instead of that render, with a fallback (DS-18, DS-19), is left | [instant-preview.md](specs/instant-preview.md) | M | — |
| 2 | Review speed on Watch (0.5× / 0.75× / 1×) — **done** (on the rendered take; instant preview passes the matched rate to `playbackRates`) | [review-speed.md](specs/review-speed.md) | S | 1 (easier after) |
| 3 | Manual alignment + speed tuning | [manual-alignment.md](specs/manual-alignment.md) | S–M | 1 |
| 4 | Layouts: side by side, stacked, take only — **done** | [layouts.md](specs/layouts.md) | S | 1 (easier after) |
| 5 | YouTube import | [youtube-import.md](specs/youtube-import.md) | S–M | access control before exposing it on the internet |
| 6 | Basic editing: crop, mirror, rotate, trim | [video-editing.md](specs/video-editing.md) | M | 1 |
| 7 | Takes at any practice speed | [practice-speeds.md](specs/practice-speeds.md) | M | — |
| 8 | Follow one dancer | [follow-dancer.md](specs/follow-dancer.md) | L | 6, background jobs, **a spike first** |

- **1 comes first.** It's the speedup the user will notice most. It also means 2, 3, 4, and 6 only need changes to the preview, plus one render at download time.
- **3 is the safety net.** It lets the user fix a match that's slightly off. Until 7 lands, it also covers takes at speeds the matcher doesn't try. And when alignment fails outright, the user can still place the take by hand.
- **Move 7 up** if anyone regularly practices at speeds other than 0.75× and 0.5×, since tuning every take by hand gets old.
- **8 is the only item with real technical risk.** Like the alignment work, it gets a go/no-go spike first. If the spike fails, there's a fallback that needs no computer vision: the user sets the crop by hand at a few points in the song.

```
instant-preview ─┬─→ review-speed
                 ├─→ manual-alignment
                 ├─→ layouts
                 └─→ video-editing ──→ follow-dancer ←── background jobs (Phase 5)
youtube-import        (independent)
practice-speeds       (independent)
```
