# Review speed

> TODO.md: "playback speed". This is part 1 of 2: slowing down the Watch screen. Part 2, handling takes filmed at any speed, is [practice-speeds.md](practice-speeds.md).

**Size:** S · **Depends on:** [instant-preview](instant-preview.md). It can be built without it, but it's simpler after.

## Goal

On Watch, the dancer can review at 0.5×, 0.75×, or 1× the song's tempo. Both videos and the sound slow down together and stay in sync.

## How

With review speed `s`:

| element   | `playbackRate` after instant-preview | before it (rendered take) |
|-----------|--------------------------------------|---------------------------|
| take      | `s / rate` (raw clip)                | `s`                       |
| reference | `s`, plus the follower nudge         | `s`, plus the follower nudge |

- The play bar still shows song time. It now advances at `s` × wall-clock time.
- The follower nudge is added to the base speed: `s + clamp(drift, ±MAX_NUDGE)`.
- Keep `preservesPitch` on (the default), so the song stays in key at 0.5×.
- When `s` equals `rate`, the raw clip plays at 1.0, exactly as it was filmed. This falls out of the formula and needs no special case.

## Key decisions

- **Only the preview slows down; downloads stay at 1×.** A slowed-down download would just be what the phone already recorded.
- **The speeds are 0.5, 0.75, and 1**, picked with a segmented control next to Sound. Its markup is the same as `SoundToggle`'s, so extract a plain `Segmented({ label, options, value, onChange })` component and use it for both.
- **Speed resets to 1× for each take.** It isn't saved anywhere.
- **One function computes the rates:** `playbackRates({ rate, speed })` in `flow.js` returns `{ take, reference }`, so the mapping is tested in one place.

## What to build

```
web/src/flow.js                           playbackRates() + tests
web/src/components/Segmented.jsx          extracted from SoundToggle
web/src/components/ComparePlayer.jsx      speed state + the control
web/src/components/useLinkedPlayback.js   base speed instead of the constant 1
```

## Acceptance criteria

- Changing speed mid-playback keeps both the position and the sync
- Room sound at 0.5× stays in pitch
- The server doesn't change, and downloads are byte-identical to before
