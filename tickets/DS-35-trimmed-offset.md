# DS-35 — `trimmed_offset`, in exactly one place per side

**Track:** Video editing · **Size:** S · **Depends on:** [DS-33](DS-33-edit-models-api.md) · **Spec:** [video-editing.md](../specs/video-editing.md)

## Context

Trimming the start moves where the output begins in the song: clip time `start_sec` heard reference time `offset_sec + start_sec × rate`. This is exactly the kind of bug the original-timeline invariant exists to catch, so it gets one helper per side and its own tests.

## Scope

- `trimmed_offset(offset_sec, rate, trim_start_sec)` in `dancesync/sync.py`, with a matching function in `flow.js`.
- The output lasts `(end_sec - start_sec) × rate`.
- Never write the shifted value back into `AlignmentResult` — the matched offset stays the offset of the clip's first sample.
- Trim changes only the output; alignment still runs on the whole clip, because more audio matches better.

## Acceptance criteria

- A rendered synthetic clip with a trim has its reference audio land where the model predicts (the `test_sync.py` approach)
- `flow.test.js` covers time mapping with a trim
- A trimmed take stays in sync with the song from its new first frame
