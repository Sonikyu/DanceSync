# DS-41 — Cache only the missing stretched rates

**Track:** Practice speeds · **Size:** S · **Depends on:** [DS-40](DS-40-coarse-rate-grid.md) · **Spec:** [practice-speeds.md](../specs/practice-speeds.md)

## Context

If the cache file lacks any requested rate, `precompute_ref_features` recomputes every rate. Going from 3 rates to 11 makes that painful: stretching is tens of seconds per rate, so adding a rate would throw away minutes of earlier work.

## Scope

- Merge newly computed rates into the existing cache file instead of rewriting it.
- Measure and record the first-alignment time against a new 3–4 minute song, before and after.

## Acceptance criteria

- Adding a rate to `RATES` computes only that rate
- A corrupt or partial cache file is detected and rebuilt rather than crashing
- The measured timings are in the PR
