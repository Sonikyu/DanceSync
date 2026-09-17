# DS-33 — Framing and trim: model and endpoints

**Track:** Video editing · **Size:** S · **Depends on:** nothing · **Spec:** [video-editing.md](../specs/video-editing.md)

## Context

Reference framing is set once per song and reused for every take, so it lives on the Reference. The take's edits live on the Clip.

## Scope

- `server/models.py`: `Crop` (fractions of the rotated, un-mirrored frame, 0..1, origin top-left), `Framing` (rotate 0/90/180/270, crop, mirror), `Trim` (seconds in the ORIGINAL uploaded clip, before re-timing). `Reference.framing = Framing()`; `Clip.framing` and `Clip.trim = None`. Defaults keep existing catalog JSON loading unchanged.
- `PUT /api/references/{id}/framing` and `PUT /api/clips/{id}/edits`.
- Validation: crop inside 0..1 and at least `MIN_CROP_FRAC` (0.2) in each dimension; `0 ≤ start < end ≤ clip duration`.

## Acceptance criteria

- Both PUTs round-trip, and validation errors return 422
- Catalog records written before this change still load
- No edit triggers a re-align
