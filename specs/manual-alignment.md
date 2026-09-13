# Manual alignment and speed tuning

> TODO.md: "manual alignment + speed tuning?"

**Size:** S–M · **Depends on:** [instant-preview](instant-preview.md), because tuning needs live feedback rather than a render after every nudge · **Related:** [practice-speeds](practice-speeds.md), which tunes the speed automatically

## Goal

On Watch, when the sync is slightly off, the dancer fixes it by hand and sees and hears the result right away. The download uses the tuned values. The same controls are also the fallback when alignment fails completely.

There are two controls, one for each symptom:

| symptom | control | changes |
|---|---|---|
| always a little early or late | **Offset**: −100 ms / −10 ms / +10 ms / +100 ms | `offset_sec` |
| in sync at the start, drifting by the end | **Speed**: −0.005 / +0.005, shown as "0.750×" | `rate` |

## Key decisions

- **A "Both" sound makes misalignment audible.** While fine-tuning, the Sound control gets a third option, **Both**. It plays the room recording (the laptop playing the song, sped up) and the clean song together. When the alignment is right, the two blend into one sound. When it's off, you hear an echo or a doubled attack. That's the quickest way to tune by ear, and instant preview makes it nearly free: just unmute both elements.
- **Manual values override the matcher's result without replacing it.**
  - `AlignmentResult` gets a new field, `manual: ManualAlignment | None`, holding `rate` and `offset_sec`. It has no score or `peak_ratio`, since those mean nothing for an alignment set by hand.
  - When `manual` is set, it's used everywhere instead of the chosen candidate: in `_chosen_candidate` in `routes/synced.py` and in `chosenCandidate` in `flow.js`.
  - The matcher's candidates stay as they are, so **Reset to automatic** only has to clear `manual`.
- **Offsets entered by hand are also in the original reference timeline** (invariant 1). The UI shows them as positions in the song.
- **The server's render cache already handles tuning, but the browser's doesn't.**
  - On the server, `_synced_id` is built from the rate and offset actually used, so a tuned render gets its own file.
  - In the browser, `syncedVideoUrl` only carries the candidate index, so it would replay the cached untuned render. Add the rate and `offset_sec` to the query string (invariant 7).
- **When alignment fails, this is where the user goes.** If no rate produces a usable match (see the Phase 5 error cases), the user doesn't hit a dead end. They drag the take onto the song timeline (`SongTimeline`) near where it starts, pick the practice speed, and then fine-tune. A later addition could be a **Snap** button that runs `match` at that rate, searching only within ±5 s of the rough position.

## API

```
PUT    /api/clips/{id}/manual   {"rate": 0.75, "offset_sec": 65.23}  → Clip
DELETE /api/clips/{id}/manual                                         → Clip (back to automatic)
```

The server checks that `0.25 ≤ rate ≤ 1.0` and that `offset_sec` lies between minus the clip's duration and the reference's duration.

## UI

A **Fine-tune** section under the player on Watch, collapsed by default:

```
Offset   [−100] [−10]  1:05.23  [+10] [+100]   ms
Speed    [−]  0.750×  [+]
Sound    Song | Room | Both
[Reset to automatic]                      [Done]
```

- Changes apply to playback immediately, and Done saves them with a `PUT`.
- `formatTime` rounds to whole seconds, so the offset display needs a variant that shows hundredths of a second.
- When manual values are in use, the caption under the player ("Matched at 1:05 · 0.75× speed") changes to say the alignment was adjusted by hand.
- On desktop, ← and → nudge the offset by 10 ms, or by 100 ms with Shift held.

## What to build

```
server/models.py                        ManualAlignment; AlignmentResult.manual
server/routes/align.py                  PUT / DELETE /api/clips/{id}/manual
server/routes/synced.py                 render the effective alignment
web/src/flow.js                         effectiveAlignment(clip) (manual, else chosen candidate) + tests
web/src/api.js                          setManualAlignment / clearManualAlignment; rate + offset in syncedVideoUrl
web/src/components/FineTune.jsx
web/src/components/useLinkedPlayback.js the "both" sound
```

## Tests

- **API:** PUT and DELETE, validation errors, a render that uses the manual values, and a different `_synced_id` once the values are tuned.
- **`flow.test.js`:** `effectiveAlignment`, and `syncedVideoUrl` changing when the values are tuned.
- **Manual check:** at the correct offset, the Both sound blends into one.

## Acceptance criteria

- A take that is 150 ms late can be fixed in a few taps, and the download matches the preview
- A take filmed at 0.8× can be tuned to stay in sync from start to finish (until practice-speeds lands, this is the only way)
- Reset to automatic restores the matcher's result exactly
- A failed alignment leads to manual placement instead of a dead end
