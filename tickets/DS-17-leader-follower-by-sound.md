# DS-17 — Leader and follower chosen by sound

**Track:** Instant preview · **Size:** M · **Depends on:** [DS-16](DS-16-clip-time-mapping.md) · **Spec:** [instant-preview.md](../specs/instant-preview.md)

## Context

`useLinkedPlayback` always treats the take as the clock and nudges the reference's `playbackRate` by up to ±10%. You can't see a muted video being nudged, but you can hear an audible one: it warbles, and it jumps when it has to seek. So whichever element is making the sound must be the clock.

## Scope

- `useLinkedPlayback.js` takes the leader from `sound` instead of hard-coding the take. The follower is always muted.
- Switching sound flips `muted` rather than swapping `src`, which makes the switch instant and removes the `resumeRef` save-and-restore in `ComparePlayer`.
- During a negative-offset lead-in there is no song yet, so the clip leads until the song starts, then the leader switches.

## Acceptance criteria

- Switching Song↔Room is instant, with no reload and no position jump
- The audible element never warbles or seeks under the nudge
- A negative-offset take plays its lead-in and hands over cleanly when the song starts
