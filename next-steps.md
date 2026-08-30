# DanceSync — Build Plan

The alignment spike is validated. This document is the roadmap for the full product build, written so each phase can be handed to Claude Code as a self-contained task.

---

## Product concept

A dancer practices to music played at reduced speed (typically 0.75x) on a laptop speaker, filming themselves on their phone. DanceSync takes that phone recording, identifies which song is playing and where in the song the clip starts, then produces a version of the video re-timed to the original speed — so the dancer can review their practice at full tempo, perfectly synced to the reference track.

### Core user flow

1. Upload a practice video (phone recording, `.mov` / `.mp4`)
2. Select or upload the reference track (the original song)
3. DanceSync extracts the audio, detects the playback rate and alignment offset
4. If the match is ambiguous (repeated chorus, low `peak_ratio`), show top-3 candidate alignments as thumbnails — the user picks the right one
5. DanceSync re-times the video to original speed and delivers the synced result

---

## Phase 1 — Production matcher

**Goal:** A clean-room Python package that reproduces the spike's alignment accuracy, with a real test suite.

### What to build

```
dancesync/
├── __init__.py
├── audio.py          # decode any supported format → mono float32 @ SR (wraps ffmpeg)
├── features.py       # chroma_cqt extraction, per-dimension z-score normalization
├── matcher.py        # sliding_correlation, peak finding, rate search, match()
├── config.py         # all tunables: SR, HOP, RATES, MIN_OVERLAP_FRAC, PEAK_EXCLUDE_SEC
└── types.py          # MatchResult dataclass (rate, offset_sec, score, peak_ratio, top_n)
```

### Key decisions

- **Do not import from `spike/`.** Re-implement from the spike as a behavioral reference. The spike's code was written for speed-of-exploration, not for production use.
- **`MatchResult` returns top-N candidates**, not just the winner. The UI needs this for the ambiguity fallback (Phase 4). Each candidate: `(rate, offset_sec, score, peak_ratio)`.
- **Offsets are always in the original reference timeline.** This invariant carries forward from the spike.
- **Caching stays.** Time-stretching a full song is tens of seconds; cache stretched reference features keyed on content hash (not mtime — production files may be re-uploaded with the same content).

### Test suite

```
tests/
├── test_matcher.py       # Tier A cases as pytest: known offset + rate recovery
├── test_features.py      # frame↔sec round-trip, normalization properties
├── test_audio.py         # format decode smoke tests (wav, mp3, m4a, mov container)
└── conftest.py           # fixtures: generate synthetic clips (port spike/synth.py logic)
```

Minimum regression: the Tier A gate — every synthetic case recovers the correct rate and lands within 50 ms tolerance. Run with `pytest tests/`. The `--demo` equivalent is `pytest tests/test_matcher.py -k synthetic`.

### Acceptance criteria

- `pytest` passes with ≥ the spike's Tier A accuracy
- `dancesync.matcher.match(clip_audio, ref_audio)` returns a `MatchResult` with top-3 candidates
- All supported audio/video container formats decode correctly
- No imports from `spike/`

---

## Phase 2 — Backend API

**Goal:** A FastAPI server that accepts uploads and runs alignment jobs.

### What to build

```
server/
├── main.py               # FastAPI app, CORS, lifespan
├── routes/
│   ├── references.py     # POST /references (upload), GET /references
│   ├── clips.py          # POST /clips (upload + auto-align), GET /clips/{id}
│   └── align.py          # POST /align (manual re-align with user-selected candidate)
├── models.py             # Pydantic models: Reference, Clip, AlignmentResult
├── storage.py            # local filesystem storage for uploaded media (abstracted for later cloud swap)
├── worker.py             # alignment job runner (sync first, background queue later)
└── config.py             # server config: upload limits, storage paths, allowed origins
```

### Key decisions

- **Sync processing first.** A 3-minute song aligns in ~10–30 seconds. For v1, the POST blocks and returns the result. Background queue (Celery/ARQ) is Phase 5 polish.
- **Storage is local filesystem** behind an abstract interface. The abstraction exists so Phase 5 can swap in S3/GCS without touching routes.
- **Upload limits:** reference tracks ≤ 50 MB, clips ≤ 500 MB (phone video). Validate content type and duration server-side.
- **CORS** configured for the frontend origin from the start.

### API shape

```
POST   /api/references          # upload a reference track
GET    /api/references          # list uploaded references
POST   /api/clips               # upload a practice video → auto-align → return top-N matches
GET    /api/clips/{id}          # get clip details + alignment result
POST   /api/clips/{id}/select   # user selects the correct candidate from top-N
GET    /api/clips/{id}/synced   # download the re-timed video (Phase 3)
```

### Acceptance criteria

- Upload a reference track and a clip via the API
- Receive a JSON response with top-3 alignment candidates (rate, offset, score, peak_ratio)
- Select a candidate; the selection persists
- `pytest` for route tests with synthetic audio fixtures

---

## Phase 3 — Video sync engine

**Goal:** Given an alignment result (rate + offset), produce a re-timed video synced to the original-speed reference.

### What to build

```
dancesync/
└── sync.py               # ffmpeg pipeline: extract audio, retime video, mux with reference
```

### Pipeline

1. **Extract audio** from the practice video (already done by the matcher, but may need the video stream separately)
2. **Speed-adjust the video** — the practice video was filmed at `rate` speed, so speed it up by `1/rate` (e.g., 0.75x practice → 1.333x speedup) using ffmpeg's `setpts` and `atempo` filters
3. **Trim** — the video starts at `offset_sec` in the reference, so the output starts there too; trim the reference audio to match the video duration
4. **Mux** — combine the sped-up video with the reference audio starting at the aligned offset
5. **Output** — `.mp4` with H.264 video + AAC audio, web-playable

### Key decisions

- **ffmpeg subprocess, not a Python binding.** `ffmpeg-python` or raw subprocess calls. The pipeline is a single complex ffmpeg command, not frame-by-frame processing.
- **No frame-level sync in v1.** The alignment is audio-based; video frames are resampled by ffmpeg's `setpts`. This is good enough for dance practice review. Frame-accurate sync (e.g., compensating for variable phone camera frame rates) is a future optimization.
- **Preserve original video quality.** Use `-crf 18` or similar; the user's phone footage is their source of truth.

### Acceptance criteria

- Given a clip, reference, rate, and offset: produce a watchable `.mp4` where the dancer's movements are at original speed and the reference audio is in sync
- Output plays correctly in browser `<video>` tags (H.264 baseline profile, AAC-LC)
- Processing time < 2x the clip duration for a 1080p input

---

## Phase 4 — Web UI

**Goal:** A web frontend for the upload → align → review → download flow.

### What to build

```
web/
├── index.html
├── src/
│   ├── App.jsx           # or App.tsx — framework TBD
│   ├── components/
│   │   ├── Upload.jsx        # drag-and-drop upload for reference + clip
│   │   ├── AlignmentReview.jsx   # show top-N candidates with score-curve viz
│   │   ├── CandidateCard.jsx     # thumbnail + offset + peak_ratio for one candidate
│   │   └── VideoPlayer.jsx       # side-by-side or synced playback of result
│   └── api.js            # fetch wrappers for the backend
└── package.json
```

### Key UX decisions

- **Two-step upload:** (1) select or upload a reference track, (2) upload the practice video. The reference is reusable across clips.
- **Alignment review screen:** Show the score curve plot (ported from the spike's `report.py`). Highlight the top-3 peaks. Each candidate gets a card with: offset timestamp, confidence (peak_ratio), and a short audio preview (a few seconds of the reference at that offset) so the user can hear which part of the song it matched to.
- **Ambiguity handling:** If `peak_ratio` is high (clear winner), skip straight to the result. If it's low, show the candidates and ask the user to pick. This is the spec's "top-3-thumbnails fallback UX."
- **Result screen:** Play the synced video. Offer download.

### Framework decision

Leave to implementer's preference. React (Vite) is the safe default. The UI is simple enough that vanilla JS + a small component library would also work. The important thing is that it's a SPA that talks to the FastAPI backend.

### Acceptance criteria

- Upload a reference + clip through the browser
- See alignment candidates with scores
- Select a candidate (or auto-select if unambiguous)
- Play and download the synced video
- Responsive layout (works on phone for quick review, desktop for detailed work)

---

## Phase 5 — Polish & deploy

**Goal:** Production-readiness.

### Tasks

- **Error handling:** Meaningful error messages for: unsupported formats, too-short clips, alignment failure (no strong peak), ffmpeg missing
- **Progress feedback:** WebSocket or SSE for alignment + video processing progress (replace the blocking POST from Phase 2)
- **Background processing:** Move alignment + sync to a task queue (ARQ or Celery) so the API returns immediately with a job ID
- **Containerization:** Dockerfile with ffmpeg, Python deps, and the web UI served from the same container (or a simple nginx + uvicorn split)
- **Storage migration:** Swap local filesystem for cloud storage (S3/GCS) behind the existing abstraction
- **Hosting:** Deploy to a single VPS (Fly.io, Railway, or similar) for v1. No multi-region, no auto-scaling yet.
- **Benchmark harness:** Port the spike spec's "week-8 benchmark harness" idea — a suite of real-world test clips with ground truth, run as CI to catch matcher regressions

### Acceptance criteria

- `docker compose up` starts the full stack
- Upload → align → sync → download works end-to-end in the browser
- CI runs the matcher regression suite on every PR

---

## Phase ordering and dependencies

```
Phase 1 (matcher)
  └─→ Phase 2 (API)
        ├─→ Phase 3 (video sync) — can start once API accepts uploads
        └─→ Phase 4 (UI) — can start once API shape is stable
              └─→ Phase 5 (polish) — after all pieces exist
```

Phases 3 and 4 can be developed in parallel once Phase 2's API shape is defined. Phase 1 is the foundation and must be done first.

---

## What to carry from the spike, what to leave

### Carry (behavioral reference)

- The chroma_cqt + z-score + sliding_correlation approach — it works
- The two-timeline offset conversion (stretched → original)
- Overlap normalization with the `MIN_OVERLAP_FRAC` floor
- `peak_ratio` as the ambiguity signal and the top-3 fallback strategy
- The Tier A test cases as regression fixtures
- The tuning parameters in `config.py` (SR=22050, HOP=512, etc.)

### Leave (spike-only concerns)

- The ingest CLI and manifest.json — the API replaces this
- The report module's CSV/plot output — the UI replaces this
- The `--demo` synthetic song generator — simplified into test fixtures
- The `--stretch clip` alternative — worth revisiting later, not in v1
- Any direct code import from `spike/`
