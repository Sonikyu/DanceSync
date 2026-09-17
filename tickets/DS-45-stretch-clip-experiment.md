# DS-45 — Experiment: stretch the clip instead of the reference

**Track:** Practice speeds · **Size:** S (timeboxed) · **Depends on:** [DS-40](DS-40-coarse-rate-grid.md) · **Spec:** [practice-speeds.md](../specs/practice-speeds.md)

## Context

The spike deferred this as `--stretch clip`. It's worth one experiment because it would make the rate grid nearly free: cost scales with the clip (30–60 s) rather than the song, there's nothing to cache, and offsets come out directly in the original timeline with no `× rate` conversion.

It has never been tested on real recordings, which is the whole question — the take is the noisy signal, and stretching it may hurt the match more than stretching the clean reference does.

## Scope

Run both approaches over Tier A and Tier B and compare match rate, offset error, and wall-clock time. Write the result up either way. This is a decision, not a feature: if it wins, it gets its own implementation ticket.

## Acceptance criteria

- A written comparison with numbers, and a go/no-go
- No production code changes in this ticket
