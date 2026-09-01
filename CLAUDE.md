# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

DanceSync is a dance practice tool. Dancers record themselves practicing to slowed-down music (typically 0.75x on a laptop speaker, filmed on a phone). The app syncs their video to the original-speed reference track so they can review their practice at full tempo, in time with the music.

The core technical premise — that a phone recording of a laptop speaker at 0.75x retains enough musical structure to match against the original — has been **validated**. The alignment spike in `spike/` passed both Tier A (synthetic) and Tier B (real-world recordings). The project is now in the full build phase.

## Repository structure

```
DanceSync/
├── spike/                    # Alignment spike (validated, not shipped)
│   ├── config.py             # SR, hop, rates, paths
│   ├── audio_io.py           # decode → mono float32 @ SR
│   ├── features.py           # chroma_cqt + z-score + frame↔sec
│   ├── matcher.py            # sliding_correlation, find_peaks, match()
│   ├── synth.py              # Tier A clip generation + demo song
│   ├── report.py             # CSV, stdout table, score-curve plots
│   ├── ingest.py             # CLI: doctor / add / scan / list / probe / label
│   ├── tier_a.py             # Tier A experiment and gate
│   └── data/                 # gitignored media + cache
├── dance-sync-spike-spec.md  # Original spike spec (for context only)
├── next-steps.md             # Phased build plan — the active roadmap
└── CLAUDE.md                 # You are here
```

Product code will live at the repo root (not inside `spike/`). The spike is reference material — its algorithms inform the production matcher, but its code is not imported or extended directly.

## Commands (spike, still valid)

```bash
bash spike/setup.sh                            # venv at repo root + deps + dependency check
brew install ffmpeg                            # required for .mov / .mp4 / .m4a / .mp3

.venv/bin/python -m spike.ingest doctor        # deps, ffmpeg, folder counts
.venv/bin/python -m spike.tier_a --demo        # smoke test against a generated fake song
.venv/bin/python -m spike.tier_a               # real Tier A run, exits non-zero if the gate fails
.venv/bin/python -m spike.tier_a --sweep       # rate x SNR x position matrix
```

`spike/README.md` has the full ingest CLI and implementation notes.

## Spike architecture (reference)

Data flows one direction: `ingest` → `audio_io` → `features` → `matcher` → `report`.

- **`audio_io`** is the only module that knows about file formats. Everything downstream sees mono float32 at `config.SR`. Video containers are accepted so their audio track can be pulled out via ffmpeg — no frame is ever decoded.
- **`config.py`** holds every tunable (`SR`, `HOP`, `RATES`, overlap floor, peak-exclusion window). Change parameters there, not inline at call sites — several of them must agree across modules to stay correct.
- **`matcher.match`** searches candidate playback rates and returns the best alignment. It works in two timelines: the reference is time-stretched to each candidate rate, so a peak found in the stretched timeline is multiplied by `rate` to get back to the original. **Every offset crossing a module boundary is in the original reference timeline** — the one you read off in Audacity. Breaking that invariant is the most likely way to produce a plausible-looking wrong answer.
- **`features.frames_to_sec`** is deliberately the single frame↔second conversion. Keep it that way.
- **`ingest`** owns `data/manifest.json`, which carries each clip's ground-truth offset, filmed rate, and condition.

Caching is load-bearing for iteration speed, not an optimization: time-stretching a full song dominates runtime, so stretched reference features are cached in `spike/data/cache/` keyed on file mtime+size.

## Key technical invariants

These carry forward from the spike into production code:

1. **Original-timeline offsets everywhere.** Every offset crossing a module boundary is in the original reference timeline. No exceptions.
2. **Single frame↔second conversion.** One function, one place. A bug shows up as a constant offset everywhere rather than as a plot/table disagreement.
3. **Overlap normalization with a floor.** Dividing correlation by overlap length prevents mid-reference bias; `MIN_OVERLAP_FRAC` prevents edge-alignment artifacts.
4. **`peak_ratio` for ambiguity detection.** Self-similar music (repeated choruses) produces tied peaks. `peak_ratio` — winner over the best peak outside an exclusion window — is the signal. When it's low, show top-3 candidates to the user instead of committing to one.
5. **Parameters in config, not inline.** Several tuning parameters must agree across modules; centralizing them prevents drift.

## Gotchas

- **Self-similar audio produces tied peaks that look like bugs.** Before chasing a matcher bug, check whether the material is repetitive — `peak_ratio` is the signal.
- **Overlap normalization needs its floor.** Without `MIN_OVERLAP_FRAC` a two-frame edge alignment wins everything.
- **Tier A failures are code bugs, not findings.** If the synthetic gate fails after a matcher change, the change broke something — don't debug with real recordings.

## Coding style

The owner of this repo reviews and debugs every line. Write code they can read in one pass.

- **Short modules.** A file over 200 lines probably does two things — split it. The spike's matcher is 253 lines and that's the upper end.
- **Flat is better than nested.** Avoid deep nesting — early returns, guard clauses, and extracting helpers all beat 4-level indentation. If a function has more than one level of `if`/`for` nesting, refactor.
- **No clever abstractions.** No metaclasses, no decorator factories, no generic base classes. A plain function that does one thing is always preferred. The right amount of abstraction is "I can delete this module and nothing else breaks."
- **Name things for what they hold, not what they do.** `offset_sec` not `result`, `clip_features` not `processed_data`. Variable names are documentation.
- **No dead code.** No commented-out blocks, no `# TODO: maybe later`, no unused imports. If it's not called, delete it.
- **Small functions.** If you can't describe what a function does in one sentence, it does too much. Aim for functions under 30 lines; if one hits 50, split it.
- **Minimal dependencies.** Every `import` is a thing to understand. Use the standard library when it's close enough. Add a third-party dep only when it saves real complexity (like librosa for audio analysis), not for convenience wrappers.
- **Explicit over implicit.** No `**kwargs` passthrough unless you're wrapping an external API. No `setattr` magic. If a function takes 5 parameters, write out 5 parameters.
- **Docstrings only where the signature isn't enough.** A function called `decode_to_mono(path: Path, sr: int) -> np.ndarray` doesn't need a docstring. A function whose units or coordinate system aren't obvious does.
- **Type hints on public interfaces.** Module-level functions and dataclass fields get type hints. Local variables don't need them.

## Development conventions

- **Python 3.11+**, dependencies in `requirements.txt` (spike) or `pyproject.toml` (product)
- **ffmpeg** is a runtime dependency — required for all audio/video decode
- **No code from `spike/` is imported into production.** Re-implement the algorithms cleanly; use the spike as a reference for behavior and edge cases.
- **Tests are mandatory for production code.** The spike had none (by design); the product does. `pytest` with the matcher's Tier A cases as the minimum regression suite.
- **All media files are gitignored.** Reference tracks, user recordings, and cache go in gitignored data directories.

## GitHub Actions

Both workflows in `.github/workflows/` run `anthropics/claude-code-action@v1` with the `CLAUDE_CODE_OAUTH_TOKEN` secret: `claude.yml` responds to `@claude` in issues/PR comments, and `claude-code-review.yml` auto-reviews every PR via the `code-review@claude-code-plugins` plugin.

## Build roadmap

See `next-steps.md` for the phased build plan. The phases are:

1. **Production matcher** — clean-room re-implementation of the spike's alignment algorithm with a proper test suite
2. **Backend API** — FastAPI server handling upload, alignment processing, and result retrieval
3. **Video sync engine** — ffmpeg-based pipeline that re-times the practice video to the original-speed reference
4. **Web UI** — upload flow, alignment review (top-3 candidates for ambiguous matches), synced video playback
5. **Polish & deploy** — error handling, progress feedback, containerization, hosting

Each phase is designed to be picked up independently by Claude Code. Start with Phase 1 — it has no external dependencies and validates that the production matcher matches the spike's accuracy.
