# DS-05 — Report an outright alignment failure

**Track:** Ship (MVP) · **Size:** S · **Depends on:** nothing · **Leads to:** [DS-26](DS-26-manual-placement-fallback.md)

## Context

`ambiguous` covers the case where several candidates tie. There's no case for no candidate being any good — a take filmed to the wrong song, or at a speed the matcher doesn't try. Today that produces a best candidate with a meaningless score and the dancer watches an out-of-sync video without being told anything went wrong.

The roadmap has this handing off to manual placement, but manual placement sits behind two post-MVP features. For the MVP this ticket ships the detection and a clear message; DS-26 turns the message into the handoff.

## Scope

- A `MIN_MATCH_SCORE` threshold in `dancesync/config.py`, set from measured Tier A and Tier B scores and written down in the PR.
- `AlignmentResult` gains a `failed: bool` alongside `ambiguous`, decided once at upload like `ambiguous` is.
- The Watch step shows a failure state instead of the player: what probably went wrong (wrong song, unusual speed, too much room noise) and what to try.

## Out of scope

Manual placement itself (DS-26).

## Acceptance criteria

- A take aligned against an unrelated song is reported as failed rather than played out of sync
- A normal take is never reported as failed (guarded by the Tier A and Tier B cases)
- `tests/test_ambiguity.py` gains a failure case beside the ambiguity cases
