# DS-24 — Fine-tune panel on Watch

**Track:** Manual alignment · **Size:** M · **Depends on:** [DS-23](DS-23-effective-alignment.md) · **Spec:** [manual-alignment.md](../specs/manual-alignment.md)

## Context

Two symptoms, two controls: always a little early or late is an offset problem; in sync at the start and drifting by the end is a speed problem.

## Scope

- `FineTune.jsx`, collapsed by default under the player: offset buttons at ±10 ms and ±100 ms, speed at ±0.005 shown as "0.750×", Reset to automatic, and Done.
- Changes apply to playback immediately; Done saves with the PUT from DS-22.
- A `formatTime` variant showing hundredths of a second, since the existing one rounds to whole seconds.
- When manual values are in use, the caption under the player says the alignment was adjusted by hand instead of "Matched at 1:05 · 0.75× speed".
- On desktop, ← and → nudge by 10 ms, and by 100 ms with Shift.

## Acceptance criteria

- A take 150 ms late can be fixed in a few taps, and the download matches the preview
- A take filmed at 0.8× can be tuned to stay in sync start to finish
- Reset to automatic restores the matcher's result exactly
