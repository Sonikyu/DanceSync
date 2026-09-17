# DS-16 — Clip↔output time mapping in `flow.js`

**Track:** Instant preview · **Size:** S · **Depends on:** nothing · **Spec:** [instant-preview.md](../specs/instant-preview.md)

## Context

Playing the raw clip in the browser needs the same timing model `sync.py` renders with, expressed as `currentTime` and `playbackRate`. Invariant 6 says the two must agree. These functions are the browser's equivalent of `frames_to_sec`: one place for the conversion.

## Scope

- `clipTimeFor(outputSec, rate)` → `outputSec / rate`, and `outputTimeFor(clipSec, rate)` → `clipSec * rate`, beside `referenceTimeFor` in `web/src/flow.js`.
- `leaderFor(sound)`: the element making the sound leads, the muted one follows.
- Vitest coverage: round trips at rates 1, 0.75, 0.5; negative offsets; the leader for each sound.

## Out of scope

Any component change — those are DS-17 and DS-18. This ticket is pure functions and tests, and can merge on its own.

## Acceptance criteria

- Round trips are exact at all three rates
- The functions are pure, with no DOM references
- The doc comment states the timing model and points at `sync.py`'s module docstring
