# DS-42 — Measure the exact rate from drift

**Track:** Practice speeds · **Size:** M · **Depends on:** [DS-40](DS-40-coarse-rate-grid.md) · **Spec:** [practice-speeds.md](../specs/practice-speeds.md)

## Context

Sync error at the end of a take is clip duration × rate error. Under 0.1 s on a 60 s clip means the rate within ±0.0017 — finer than any grid worth searching. So: find it on the coarse grid, then measure the rate.

## Scope

- A new module `dancesync/rate.py` — `matcher.py` is already 207 lines.
- Match the first and second halves separately at the coarse winner's rate, each searched only within ±`PEAK_EXCLUDE_SEC` of the coarse position so a half can't jump to another chorus. Then `rate = (offset_b - offset_a) / (start_b - start_a)`.
- Equal-length halves cancel the coarse rate's error: a sub-clip matched at a slightly wrong rate lines up best around its middle, so both halves shift by the same amount and the difference is unaffected.
- No new stretches: the halves reuse the coarse rate's cached features, so only correlation runs again.
- Correct each candidate's offset for the refined rate with the same model: `offset -= (refined - coarse) × clip_len / 2`. Validate against synthetic clips with known offsets; if the model isn't accurate enough, re-run `match` at the refined rate instead and note the added cost.
- Snap to a multiple of 0.01 within `RATE_SNAP_TOL` (0.003), since players use round speeds. Round the stored rate to 4 decimals either way.
- Skip refinement below `MIN_REFINE_CLIP_SEC` (~20 s): the halves are too short to match and too close together to measure.

## Acceptance criteria

- A synthetic 60 s take at 0.8× renders with under 100 ms of drift at the end
- Unit tests cover the drift formula, the error cancellation, snapping, and the short-clip skip
- Tests that aren't about rates pass `rates=` explicitly, so the suite stays fast
