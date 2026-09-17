# DS-25 — A "Both" sound for tuning by ear

**Track:** Manual alignment · **Size:** XS · **Depends on:** [DS-17](DS-17-leader-follower-by-sound.md), [DS-24](DS-24-fine-tune-ui.md) · **Spec:** [manual-alignment.md](../specs/manual-alignment.md)

## Context

The fastest way to tune alignment is by ear. Playing the room recording and the clean song together makes error audible: right, and they blend into one sound; wrong, and you hear an echo or a doubled attack. Instant preview makes this nearly free — unmute both elements.

## Scope

- A third Sound option, Both, unmuting both elements. The clip keeps leading, since the reference is the one that can be nudged inaudibly against it.
- Preview only. Downloads keep Song and Room, because a mixed download has no use.

## Acceptance criteria

- At the correct offset the two blend into one sound; 100 ms out is clearly audible
- The download options are unchanged
