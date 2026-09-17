# DS-38 — Adjust mode: crop, mirror, rotate

**Track:** Video editing · **Size:** M · **Depends on:** [DS-37](DS-37-framing-preview.md) · **Spec:** [video-editing.md](../specs/video-editing.md)

## Context

References are usually landscape with a group across the frame; takes are usually portrait with the dancer small in the middle of a room. Side by side, the two dancers come out at very different sizes.

## Scope

- **Adjust** under each video pauses playback and shows a crop box that can be dragged and resized, using pointer events so touch works. **Mirror** and **Rotate** sit beside it. **Reset** clears; **Done** saves with the PUT from DS-33.
- A crop drawn on a mirrored preview is converted before storing: `x = 1 - x_drawn - w`.
- `MIN_CROP_FRAC = 0.2` is enforced in the UI as well as the API — a tighter crop of a 1080p frame is upscaled more than ~3× in the 720p compare render and turns to mush.
- Rotate is a manual override only, for footage whose metadata is wrong (a phone lying flat). ffmpeg and browsers already honour correct rotation metadata.

## Acceptance criteria

- Cropping a group reference to one dancer and a portrait take to the dancer makes the two a similar size side by side
- The crop box works with touch on a phone
- A crop drawn while mirrored keeps the dancer inside it when mirror is toggled
