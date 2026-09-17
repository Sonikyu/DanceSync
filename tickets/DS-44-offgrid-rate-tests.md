# DS-44 — Off-grid rate coverage and display

**Track:** Practice speeds · **Size:** S · **Depends on:** [DS-42](DS-42-rate-refinement.md) · **Spec:** [practice-speeds.md](../specs/practice-speeds.md)

## Scope

- Tier A cases at 0.7, 0.8, 0.85, and 0.9, at the usual positions and SNRs. Rate within ±0.005 and offset within 50 ms.
- At least one real phone recording at 0.8× or 0.9× that matches and renders in sync (Tier B), added to DS-11's fixtures if that exists.
- `formatRate` rounds refined rates for display: "0.8× speed", "0.83× speed".

## Acceptance criteria

- All four off-grid rates pass the Tier A gate
- One real off-grid recording matches and renders in sync
- The UI never shows a rate like "0.8300000001×"
