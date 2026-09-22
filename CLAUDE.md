# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

DanceSync is a dance practice tool. Dancers record themselves practicing to slowed-down music, typically at 0.75x on a laptop speaker, filmed on a phone. The app syncs the video to the original-speed reference track, so dancers can review their practice at full tempo, in time with the music and next to the original choreography.

**Status:** The MVP is built. That covers the production matcher (`dancesync/`), the FastAPI backend (`server/`), the ffmpeg sync engine, and the React web UI (`web/`). What remains is Phase 5 polish and the post-MVP features. Both are tracked in `next-steps.md`, and each feature has its own spec in `specs/`. The spike in `spike/` validated the alignment premise on both synthetic (Tier A) and real-world (Tier B) recordings.

**Audience:** The owner and friends. It runs locally or self-hosted; it is not a public site.

## Repository structure

```
DanceSync/
├── dancesync/                # Python library: matching + rendering (no web code)
│   ├── config.py             # every tunable: SR, HOP, RATES, thresholds, encoder settings, cache dir
│   ├── audio.py              # decode any container → mono float32 @ SR (the only module that knows formats)
│   ├── features.py           # chroma_cqt + z-score, frames_to_sec
│   ├── matcher.py            # sliding correlation, peaks, rate search, match()
│   ├── types.py              # Candidate, MatchResult
│   ├── sync.py               # what to render: ffmpeg filtergraphs for the synced / side-by-side video
│   └── ffmpeg.py             # how to run ffmpeg: presence check, probe, encoder args, atomic writes
├── server/                   # FastAPI app
│   ├── main.py               # app, CORS, routers
│   ├── routes/               # references, clips, align (candidate select), synced
│   ├── models.py             # Pydantic request/response bodies + persisted records
│   ├── storage.py            # raw bytes on disk, keyed by content hash
│   ├── catalog.py            # JSON metadata records (kept separate from storage)
│   ├── worker.py             # align_clip / sync_clip (synchronous for now)
│   └── config.py             # storage root, upload limits, CORS origins
├── web/                      # React 19 + Vite SPA
│   └── src/
│       ├── App.jsx           # step machine: song → video → match (only if ambiguous) → watch
│       ├── flow.js           # pure helpers (timing, formatting), unit-tested with Vitest
│       ├── api.js            # fetch/XHR wrappers + dancer-facing error messages
│       └── components/       # one component per step, plus the player pieces
├── tests/                    # pytest: Tier A matcher regression, ambiguity, API, real renders
├── specs/                    # one spec per post-MVP feature
├── spike/                    # alignment spike (validated; reference only, never imported)
├── next-steps.md             # status + roadmap
├── TODO.md                   # ideas inbox; specced ideas link into specs/
└── dance-sync-spike-spec.md  # original spike spec (history)
```

## Commands

```bash
brew install ffmpeg                                   # runtime dependency for all decode + render
python3 -m venv .venv && .venv/bin/pip install -e '.[dev]'
npm --prefix web install

.venv/bin/uvicorn server.main:app --port 8000         # API
npm --prefix web run dev                              # UI on :5173, proxies /api to :8000 (override: DANCESYNC_API_URL)

.venv/bin/python -m pytest                            # full suite, ~1 min (renders real video)
.venv/bin/python -m pytest tests/test_matcher.py      # Tier A regression only
npm --prefix web test                                 # Vitest
```

`.claude/launch.json` defines the `api` and `web` preview servers, plus `api-8001` and `web-8001` for running a second copy. The spike has its own CLI (`python -m spike.tier_a`, `spike.ingest`), documented in `spike/README.md`. You only need it when revisiting the experiment.

## Architecture

- **Align** (runs on clip upload and blocks the request):
  1. `routes/clips.py` calls `storage.save`, which assigns a content-hash id.
  2. `worker.align_clip` decodes the audio with `audio.decode`.
  3. `matcher.precompute_ref_features` builds the stretched reference features, cached per reference id.
  4. `matcher.match` produces the `AlignmentResult`: the top 3 candidates plus the `ambiguous` flag. It's saved in the catalog.
- **Render** (runs on `HEAD`/`GET /api/clips/{id}/synced`):
  1. `routes/synced.py` picks the chosen candidate, or the best one if the user never picked.
  2. `worker.sync_clip` calls `sync.render_synced` or `sync.render_side_by_side`.
  3. `ffmpeg.run_to_file` writes the output. Its filename encodes every input, so an existing file is served as-is.
- **Watch** (in the browser): `ComparePlayer` plays the rendered take and the reference media on one play bar. `useLinkedPlayback` treats the take as the clock and nudges the muted reference's `playbackRate` to keep up.

`dancesync/` never imports from `server/`, and `server/` reaches the matcher and renderer only through `worker.py`.

## Key technical invariants

1. **Original-timeline offsets everywhere.** Every offset that crosses a module boundary is in the original reference timeline, the one you'd read off in Audacity. No exceptions. Breaking this is the most likely way to get a plausible-looking wrong answer.
2. **One frame↔second conversion.** It lives in `features.frames_to_sec` and nowhere else, so a bug shows up as a constant offset everywhere rather than a plot/table disagreement.
3. **Overlap normalization with a floor.** Dividing correlation by overlap length prevents mid-reference bias, and `MIN_OVERLAP_FRAC` prevents edge-alignment artifacts.
4. **`peak_ratio` detects ambiguity.** Self-similar music (repeated choruses) produces tied peaks. `peak_ratio` is the winner divided by the best peak outside an exclusion window. At upload, `AMBIGUOUS_PEAK_RATIO` (1.2, measured) decides whether the user has to pick from the top 3.
5. **Parameters live in config, not inline.** Several must agree across modules.
6. **Renders and playback share one timing model.** Clip time `t` heard reference time `offset_sec + t × rate`. Output time `T` shows clip time `T / rate` over reference time `offset_sec + T`. `sync.py`'s module docstring states this for ffmpeg, and `flow.referenceTimeFor` states it for the browser. If you change one, change the other.
7. **Render cache names encode every input.** `_synced_id` in `routes/synced.py` names each render after the clip, reference, rate, offset, layout, and sound. Anything new that changes the picture or audio (edits, layouts, speeds) must go into that name *and* into the URL query in `api.syncedVideoUrl`. Otherwise the server or the browser serves a stale file.

## Gotchas

- **Self-similar audio produces tied peaks that look like bugs.** Before chasing a matcher bug, check whether the material is repetitive; `peak_ratio` will tell you.
- **Overlap normalization needs its floor.** Without `MIN_OVERLAP_FRAC`, a two-frame edge alignment wins everything.
- **Tier A failures are code bugs, not findings.** If the synthetic gate fails after a matcher change, the change broke something. Don't debug it with real recordings.
- **iOS Safari won't fetch a `<video>` source until play is pressed.** So the UI sends a `HEAD` to `/synced` to trigger the render before handing the URL to the player. iOS also lets an element play unmuted only if a user gesture started it.
- **Two `<video>` elements never stay in lockstep on their own.** One is the clock, and the other is steered: small `playbackRate` nudges, with a seek only past 0.5 s of drift. Seeking on every drift stalls on keyframe decodes.
- **Re-timed takes have unusual frame rates.** A 30 fps clip at 0.75x becomes 40 fps. `-fps_mode passthrough` and `-enc_time_base:v filter` keep every frame, because resampling to 30 visibly stutters. The side-by-side render puts both inputs on a 60 fps grid before `hstack`.
- **`peak_ratio` can be infinite** when nothing competes with the winner. The API sends it as `null`.
- **The full pytest run takes about a minute,** because the sync tests render real video. librosa's "empty frequency set" warnings on synthetic audio are expected.

## Coding style

The owner of this repo reviews and debugs every line. Write code they can read in one pass.

- **Short modules.** A file over 200 lines probably does two things, so split it. The spike's matcher is 253 lines, and that's the upper end.
- **Flat is better than nested.** Early returns, guard clauses, and extracted helpers all beat 4-level indentation. If a function has more than one level of `if`/`for` nesting, refactor it.
- **No clever abstractions.** No metaclasses, no decorator factories, no generic base classes. A plain function that does one thing is always preferred. The right amount of abstraction is "I can delete this module and nothing else breaks."
- **Name things for what they hold, not what they do.** `offset_sec`, not `result`. `clip_features`, not `processed_data`. Variable names are documentation.
- **No dead code.** No commented-out blocks, no `# TODO: maybe later`, no unused imports. If it's not called, delete it.
- **Small functions.** If you can't describe what a function does in one sentence, it does too much. Aim for under 30 lines, and split any function that reaches 50.
- **Minimal dependencies.** Every `import` is a thing to understand. Use the standard library when it's close enough. Add a third-party dependency only when it saves real complexity (like librosa for audio analysis), not for convenience wrappers.
- **Explicit over implicit.** No `**kwargs` passthrough unless you're wrapping an external API. No `setattr` magic. If a function takes 5 parameters, write out 5 parameters.
- **Docstrings only where the signature isn't enough.** `decode_to_mono(path: Path, sr: int) -> np.ndarray` doesn't need one. A function whose units or coordinate system aren't obvious does.
- **Type hints on public interfaces.** Module-level functions and dataclass fields get type hints. Local variables don't need them.
- **Frontend:** function components and hooks, plain CSS in `styles.css`, no state library, no UI kit, and only `react`/`react-dom` at runtime. Put any logic that can be pure in `flow.js` with a Vitest test, and keep components thin.

## Development conventions

- **Python 3.11+**, with dependencies in `pyproject.toml` (the spike keeps its own `requirements.txt`). **Node 20.19+ or 22.12+** for Vite.
- **ffmpeg** is a runtime dependency, required for all audio/video decoding and rendering.
- **No code from `spike/` is imported into production.** Use the spike as a reference for behavior and edge cases.
- **Tests are mandatory for production code.** Python code needs pytest, with the Tier A cases as the minimum regression suite. Frontend helpers in `flow.js` need Vitest tests.
- **All media files are gitignored:** `.data/server/` (uploads, catalog, renders), `.cache/dancesync/` (decoded audio, stretched features), and `spike/data/`.

## GitHub Actions

`test.yml` runs `pytest` (with ffmpeg installed), Vitest, and a `web` build on every PR and on pushes to `main`. The other two workflows run `anthropics/claude-code-action@v1` with the `CLAUDE_CODE_OAUTH_TOKEN` secret. `claude.yml` responds to `@claude` in issue and PR comments, and `claude-code-review.yml` auto-reviews every PR through the `code-review@claude-code-plugins` plugin.

## Roadmap

`next-steps.md` holds the status of Phases 1–5 and the ordered list of post-MVP features. Each feature has a self-contained spec in `specs/`. To pick one up, read its spec and the files it names. New ideas go in `TODO.md` until they're specced.
