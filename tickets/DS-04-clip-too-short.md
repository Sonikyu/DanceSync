# DS-04 — Reject clips too short to match

**Track:** Ship (MVP) · **Size:** S · **Depends on:** nothing · **Spec:** [next-steps.md](../next-steps.md) Phase 5 error cases

## Context

A clip of a few seconds can't produce a trustworthy correlation peak, but today it goes through the full align path and comes back with a confident-looking wrong answer.

## Scope

- A `MIN_CLIP_SEC` constant in `dancesync/config.py` (start at 10 s; note the measurement that set it).
- `server/worker.py` checks the decoded duration before matching and raises a typed error.
- `routes/clips.py` maps it to 422 with a message naming the minimum.
- `web/src/api.js` gets the dancer-facing wording: how long the clip was and how long it needs to be.

## Acceptance criteria

- A 5 s clip is rejected with a message saying how long a take needs to be
- A clip just over the minimum still aligns
- `tests/test_api.py` covers the rejection and the boundary
