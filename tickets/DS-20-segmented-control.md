# DS-20 — Extract a shared `Segmented` control

**Track:** Review speed · **Size:** XS · **Depends on:** nothing · **Spec:** [review-speed.md](../specs/review-speed.md)

## Context

Sound is a segmented control today. Speed (DS-21) and Layout (DS-29) want the same markup and styling. Extracting it once avoids three near-copies.

## Scope

- `web/src/components/Segmented.jsx`: `Segmented({ label, options, value, onChange })`, presentational only.
- `SoundToggle` becomes a thin use of it. Styles move to the shared class in `styles.css`.
- Keyboard and screen-reader behaviour: arrow keys move between options, the group is labelled.

## Acceptance criteria

- The Sound control looks and behaves exactly as before
- The component holds no state of its own
