# DS-40 — Coarse rate grid and candidate dedupe

**Track:** Practice speeds · **Size:** M · **Depends on:** nothing (measure with [DS-11](DS-11-benchmark-harness.md) if it exists) · **Spec:** [practice-speeds.md](../specs/practice-speeds.md)

## Context

`RATES = (1.0, 0.75, 0.5)`. YouTube's custom speed moves in 0.05 steps and practice apps go to 1%. A take at 0.8× gets matched at 0.75× and drifts 3 s by the end of a minute.

## Scope

- `RATES` becomes 0.50 to 1.00 in steps of 0.05. The algorithm is unchanged.
- **First, verify with Tier A that a peak still appears when the rate is up to 0.025 off.** Chroma changes slowly, so it probably does for 30–60 s clips; if not, use 0.025 steps. Record the finding in the PR.
- Merge candidates whose original-timeline offsets are within `PEAK_EXCLUDE_SEC`, keeping the best score. Without this, neighbouring rates find the same passage and the top 3 becomes one chorus at three adjacent rates, which breaks the Match screen and `test_ambiguity.py`.

## Acceptance criteria

- The existing 1.0, 0.75, 0.5 cases pass unchanged
- `test_ambiguity.py` still offers both choruses
- The off-grid tolerance finding is written down in the PR
