# DS-47 — Fallback: keyframed crop

**Track:** Follow dancer · **Size:** M · **Depends on:** [DS-36](DS-36-render-with-edits.md), [DS-46](DS-46-follow-dancer-spike.md) failing · **Spec:** [follow-dancer.md](../specs/follow-dancer.md)

## Context

If the spike fails the gate, the user can still follow a dancer by hand: set the crop at a few moments in the song and let it move linearly between them. Same plumbing, no computer vision, no new dependency.

## Scope

- Keyframes stored on the Reference: `(time_sec, crop)` in original reference-timeline seconds (invariant 1).
- The crop size stays fixed for the whole song and only the position moves — a crop that resizes makes the dancer seem to breathe in and out. Size comes from the largest keyframed box.
- Path sampled at 10 fps and linearly interpolated, in the player and the render alike. Built with pure numpy in `dancesync/follow.py`, unit-testable without video.
- Render: generate an ffmpeg `sendcmd` script with one `crop` x/y command per sample, so no frames are decoded in Python.
- Preview: `requestVideoFrameCallback` on the reference `<video>` sets the transform from the path at `currentTime`, falling back to `requestAnimationFrame`.
- UI: set a keyframe at the current position, list them, delete one.

## Acceptance criteria

- A dancer stays in frame across a formation change with a handful of keyframes
- The motion is smooth in both preview and render, and they agree
- Path maths is unit-tested without touching video
