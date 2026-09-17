# DS-22 — Manual alignment: model and endpoints

**Track:** Manual alignment · **Size:** S · **Depends on:** nothing · **Spec:** [manual-alignment.md](../specs/manual-alignment.md)

## Context

Manual values must override the matcher's result without replacing it, so "Reset to automatic" only has to clear one field.

## Scope

- `server/models.py`: `ManualAlignment` holding `rate` and `offset_sec` — no score, no `peak_ratio`, since neither means anything for an alignment set by hand — and `AlignmentResult.manual: ManualAlignment | None = None`. The default keeps existing catalog JSON loading unchanged.
- `PUT /api/clips/{id}/manual` and `DELETE /api/clips/{id}/manual`, both returning the Clip.
- Validation: `0.25 ≤ rate ≤ 1.0`, and `offset_sec` between minus the clip duration and the reference duration.
- Offsets set by hand are in the original reference timeline, like every other offset (invariant 1).

## Acceptance criteria

- PUT then GET returns the manual values; DELETE restores the matcher's result exactly
- Out-of-range rate and offset return 422
- Catalog records written before this change still load
