# DS-23 — Use the effective alignment everywhere

**Track:** Manual alignment · **Size:** S · **Depends on:** [DS-03](DS-03-render-params-record.md), [DS-22](DS-22-manual-alignment-api.md) · **Spec:** [manual-alignment.md](../specs/manual-alignment.md)

## Context

Once `manual` exists, every consumer must prefer it over the chosen candidate — and the caches on both sides must notice. The server's cache name is already built from the rate and offset actually used; the browser's URL only carries the candidate index, so without this it replays the untuned render.

## Scope

- `effectiveAlignment(clip)` in `flow.js` — manual if set, else the chosen candidate — with tests.
- `_chosen_candidate` in `routes/synced.py` uses the effective alignment.
- Rate and offset go into the render params record from DS-03, so they reach both the cache name and the query string (invariant 7).

## Acceptance criteria

- A tuned clip renders a different file from the untuned one, and the browser requests that file
- Clearing the manual values returns both sides to the original render
- `flow.test.js` covers `effectiveAlignment` and the URL changing when values are tuned
