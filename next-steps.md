# DanceSync — Build Plan

The alignment spike validated the approach, and the MVP (Phases 1–4) is built: upload a song and a practice video, align them, confirm the match when it's ambiguous, and watch or download the synced result. Phase 5's MVP items are done (CI, error cases, one-command Docker run, access control), and so are the first six post-MVP features (instant preview, review speed, manual alignment, layouts, YouTube import, video editing). What's left is the rest of Phase 5 (job queue, benchmark harness) and post-MVP features 7–9. Each feature is specced in [`specs/`](specs/) so it can be handed to Claude Code as a self-contained task, and each spec is broken into day-sized tickets in [`tickets/`](tickets/). **This file holds status and rationale; [`tickets/README.md`](tickets/README.md) holds the working order.**

**Audience:** the owner and friends, running DanceSync locally or self-hosted rather than as a public site. That shapes Phase 5, which needs basic access control but nothing for multiple tenants, and it's what makes YouTube import viable.

---

## Product concept

A dancer practices to music played at reduced speed (typically 0.75x) on a laptop speaker, filming themselves on their phone. DanceSync takes that recording and finds where in the song it starts and how fast the song was playing. It then re-times the video to the original speed, so the dancer can review the practice at full tempo, in sync with the reference track, next to the original choreography.

### User flow (as built)

1. **Song:** pick a song used before, upload a new one (an audio file, or a video of the choreography), or paste a YouTube link to one.
2. **Video:** upload the practice video. The server aligns it, which takes 10–30 s.
3. **Match:** this step appears only when the match is ambiguous (a repeated chorus, `peak_ratio` < 1.2). It shows the top 3 candidates on a song timeline and plays 8 s of the song at each one, and the user picks the right one.
4. **Watch:** plays as soon as alignment finishes. The browser plays the uploaded video itself, sped up to full tempo, next to the reference video, with one play bar for both; nothing is rendered until Download. The sound can be the song or the room (the phone's own recording). The user can slow the review to 0.5× or 0.75×, pick a layout (side by side, stacked, or take only), fine-tune a slightly-off match by ear, crop, mirror or rotate either video and trim the take, and download exactly what's on screen.
5. **No match:** when the take can't be found in the song, the user places it by hand on the song's timeline and fine-tunes from there.

---

## Status

| Phase | Status |
|---|---|
| 1. Production matcher | Done |
| 2. Backend API | Done |
| 3. Video sync engine | Done |
| 4. Web UI | Done |
| 5. Polish & deploy | MVP items done (CI, error cases, Docker, access control), plus the render cache cap and the hosting runbook. Left: job queue with progress, benchmark harness |
| Post-MVP features | 1–6 done (instant preview, review speed, manual alignment, layouts, YouTube import, video editing); 7–9 specced in [`specs/`](specs/) |

### Checks still owed

The code for these is merged and tested, but each one needs a real device or a real server that CI doesn't have:

- **Instant preview on real browsers** (DS-19): play a phone's take on Watch in iPhone Safari, desktop Safari, Chrome, and Firefox, including an HEVC take that should fall back to a render.
- **YouTube import from a VPS** (DS-31): datacenter IPs are often blocked with "confirm you're not a bot". Record the result in [`docs/hosting.md`](docs/hosting.md#youtube-import-from-this-host).
- **The crop box on a phone's touchscreen** (DS-38).

### What's next

Pick by what hurts most:

1. **Practice speeds** (feature 7, DS-40–DS-45) if anyone practices at speeds other than full, ¾, and ½. Today those takes need the speed set by hand in Fine-tune.
2. **Job queue and progress** (DS-13, DS-14) before hosting behind a proxy with a short timeout, and before follow dancer. Today an upload blocks for 10–30 s with no progress, and a long render blocks its request.
3. **Benchmark harness** (DS-11) before any more matcher changes.
4. **Managed hosting on Render** (feature 9) if running a VPS is more upkeep than the group wants.

Invariant 7 (render cache names) is enforced by one `RenderParams` record shared by the server's cache id and the browser's URL, with a test that fails if they drift (DS-03).

pytest covers the Tier A matcher regression, the ambiguity threshold, the API routes, and real ffmpeg renders. Vitest covers the UI's pure helpers in `web/src/flow.js`, `web/src/tuning.js` and `web/src/editing.js`, and `api.js`'s URL building.

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
- `POST /api/references`, `POST /api/references/import` (a YouTube link; post-MVP), `GET /api/references`, `GET /api/references/{id}/media`
- `PUT /api/references/{id}/framing` (crop, mirror, rotate for the song's video; post-MVP)
- `POST /api/clips`, `GET /api/clips/{id}`, `GET /api/clips/{id}/media` (the uploaded take, with range requests; for instant preview), `POST /api/clips/{id}/select`, `PUT|DELETE /api/clips/{id}/manual` (an alignment set by hand; post-MVP), `PUT /api/clips/{id}/edits` (the take's framing and trim; post-MVP)
- `GET|HEAD /api/clips/{id}/synced?sound=song|room&layout=take|side-by-side|stacked` (the URL also carries the alignment and a hash of the edits, so a changed input never serves a stale render)
- `GET|POST /api/session` (sign-in status and sign-in, when a passphrase is set; Phase 5)

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
- **Watch screen:** built as a rendered video at first; instant preview (post-MVP) replaced that. Now:
  - The browser plays the uploaded take and the reference on one play bar. Whichever element makes the sound is the clock, and the muted one follows by nudging its `playbackRate` (`useLinkedPlayback.js`).
  - If the browser can't decode the take (HEVC in Firefox, for one), it plays a server render instead.
  - Sound, review speed, layout, Fine-tune, Adjust, and one Download button that renders what's on screen.
- **Pure helpers** live in `web/src/flow.js`, `tuning.js` (fine-tuning, placing by hand), and `editing.js` (Adjust), with Vitest tests.

---

## Phase 5 — Polish & deploy

Ticketed as three separate tracks — Ship (what's left before the MVP is done), Operate, and Platform. See [`tickets/README.md`](tickets/README.md).

- **Tests in CI (MVP):** done. `.github/workflows/test.yml` runs `pytest`, `npm --prefix web test`, and a web build on every PR and on pushes to `main`. Tests that need the internet (a real YouTube import) are marked `network` and run only with `pytest -m network`.
- **Error cases (MVP):** done. Friendly messages for files that are too big, unsupported file types, an unreachable server, and failed YouTube imports, plus:
  - clips too short to match: `MIN_CLIP_SEC` = 10 s, measured; the upload answers 422 with the clip's length.
  - no strong peak anywhere: `MIN_MATCH_SCORE` = 3.5, measured; `AlignmentResult.failed` and a "couldn't find this take" screen that leads to placing the take by hand ([manual-alignment](specs/manual-alignment.md), DS-26), with a "watch anyway" escape.
  - a startup check that stops the server if ffmpeg is missing.
- **One-command run (MVP):** done. A multi-stage `Dockerfile` (Node builds `web/dist`, Python 3.11 slim with ffmpeg runs it), FastAPI serving that build from the API's origin (`server/web.py`), and `docker compose up` with named volumes for data and cache. Settings come from `DANCESYNC_*` env vars (`.env.example`).
- **Access control:** done. Set `DANCESYNC_PASSPHRASE` and every `/api` request needs the cookie from `POST /api/session`; the web app shows a sign-in screen. Unset means no sign-in, as before.
- **Render cleanup:** done. Renders are capped at `DANCESYNC_RENDER_CACHE_GB` (5 GB by default); after each new render, the least recently served ones are deleted (`server/render_cache.py`) and re-rendered on demand.
- **Background jobs and progress (not started, DS-13, DS-14):** move alignment and rendering to a job queue that reports progress over server-sent events (SSE). Needed for:
  - [follow-dancer](specs/follow-dancer.md), where tracking takes minutes
  - any reverse proxy with a 60 s timeout in front of a long render
- **Hosting:** runbook in [`docs/hosting.md`](docs/hosting.md): a small VPS with Docker and Caddy (600 s proxy timeouts, from measured render times), or a home machine over Tailscale. Trying a YouTube import from the VPS is still owed (see [Checks still owed](#checks-still-owed)).
- **Benchmark harness (not started, DS-11):** real-world clips with known correct offsets, run in CI to catch matcher regressions.
- **Deferred: cloud storage (S3/GCS).** A self-hosted deployment for the owner and friends doesn't need it. `server/storage.py` stays separate so it can be swapped in later.

---

## Post-MVP features

These come from `TODO.md`, and each one has its own spec. Recommended order:

| # | Feature | Spec | Size | Depends on |
|---|---|---|---|---|
| 1 | Instant preview (watch before rendering) — **done**; DS-19's manual browser matrix on a real iPhone and Safari is still owed | [instant-preview.md](specs/instant-preview.md) | M | — |
| 2 | Review speed on Watch (0.5× / 0.75× / 1×) — **done** | [review-speed.md](specs/review-speed.md) | S | 1 (easier after) |
| 3 | Manual alignment + speed tuning — **done** (fine-tune panel, Both sound, manual placement on failure) | [manual-alignment.md](specs/manual-alignment.md) | S–M | 1 |
| 4 | Layouts: side by side, stacked, take only — **done** | [layouts.md](specs/layouts.md) | S | 1 (easier after) |
| 5 | YouTube import — **done**; a real download from a VPS is still to be tried | [youtube-import.md](specs/youtube-import.md) | S–M | access control before exposing it on the internet |
| 6 | Basic editing: crop, mirror, rotate, trim — **done**; the crop box on a real phone's touchscreen is still to be tried | [video-editing.md](specs/video-editing.md) | M | 1 |
| 7 | Takes at any practice speed | [practice-speeds.md](specs/practice-speeds.md) | M | — |
| 8 | Follow one dancer | [follow-dancer.md](specs/follow-dancer.md) | L | 6, background jobs, **a spike first** |
| 9 | One-click managed hosting (Render), for the same owner-and-friends group | [managed-hosting.md](specs/managed-hosting.md) | S | — on Render; background jobs on Fly.io |

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
managed-hosting       (independent)
practice-speeds       (independent)
```
