# DS-21 — Review at 0.5× / 0.75× / 1×

**Track:** Review speed · **Size:** S · **Depends on:** [DS-18](DS-18-play-raw-clip.md), [DS-20](DS-20-segmented-control.md) · **Spec:** [review-speed.md](../specs/review-speed.md)

## Context

Reviewing a fast passage needs slow motion on both videos and the sound at once.

## Scope

- `playbackRates({ rate, speed })` in `flow.js` returns `{ take, reference }` — take `s / rate`, reference `s` — with tests. One function, so the mapping is tested in one place.
- `useLinkedPlayback` nudges around the base speed instead of around 1: `s + clamp(drift, ±MAX_NUDGE)`.
- A `Segmented` speed control next to Sound. Speed resets to 1× per take and is not persisted.
- `preservesPitch` stays on, so the song stays in key at 0.5×.
- The play bar still shows song time, now advancing at `s` × wall clock.

## Out of scope

Slowed-down downloads — a slowed download is just what the phone already recorded.

## Acceptance criteria

- Changing speed mid-playback keeps both position and sync
- Room sound at 0.5× stays in pitch
- When `s` equals `rate` the raw clip plays at exactly 1.0, with no special case in the code
- The server is untouched and downloads are byte-identical
