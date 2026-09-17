# DS-07 — FastAPI serves the built frontend

**Track:** Ship (MVP) · **Size:** S · **Depends on:** nothing · **Spec:** [next-steps.md](../next-steps.md) Phase 5

## Context

In dev, Vite proxies `/api`, so the browser talks to one origin. In production there's no proxy, so the two would end up on different origins and CORS would become load-bearing. Serving `web/dist` from FastAPI keeps production on one origin too.

## Scope

- Mount `web/dist` as static files in `server/main.py`, after the API routers so `/api/*` always wins.
- An SPA fallback: any unmatched non-`/api` path serves `index.html`.
- Only mount when the directory exists, so dev is unaffected.
- `server/config.py` gets the dist path.

## Acceptance criteria

- With `web/dist` built, `/` serves the app and `/api/references` still answers JSON
- A deep link reloads correctly instead of 404ing
- Running the dev server without a build is unchanged
