# DS-26 — Manual placement when alignment fails

**Track:** Manual alignment · **Size:** S · **Depends on:** [DS-05](DS-05-alignment-failed.md), [DS-24](DS-24-fine-tune-ui.md) · **Spec:** [manual-alignment.md](../specs/manual-alignment.md)

## Context

DS-05 detects an outright failure and shows a message. This turns that dead end into a way forward, which is what the roadmap always intended — it just couldn't ship at MVP time, because it needs instant preview and the fine-tune panel underneath it.

## Scope

- On the failure state, the user drags the take onto the song timeline (`SongTimeline`) near where it starts and picks the practice speed. That writes a `ManualAlignment` and moves them to Watch with the fine-tune panel open.
- Reuse `SongTimeline` from the Match step rather than building a second timeline.

## Out of scope

The **Snap** button — re-running `match` at the chosen rate within ±5 s of the rough position. Worth doing, but only once rough placement proves useful.

## Acceptance criteria

- A failed alignment leads to manual placement instead of a dead end
- A take placed roughly and then tuned by ear ends up in sync
- The failure message no longer appears without a way forward
