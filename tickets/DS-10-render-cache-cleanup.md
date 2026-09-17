# DS-10 — Cap the render cache

**Track:** Operate · **Size:** S · **Depends on:** nothing · **Spec:** [next-steps.md](../next-steps.md) Phase 5

## Context

Renders in `.data/server/synced/` are never deleted. Every take, sound, and layout combination leaves a file behind, so a self-hosted box fills up quietly.

## Scope

- A size cap in `server/config.py` (start at 5 GB).
- A sweep that deletes least-recently-used renders until the total is under the cap, using file mtime, touched on each serve.
- Run it after each successful render, not on a timer — renders are the only thing that grows the directory.
- Never delete a file currently being written (the atomic temp-then-rename path already distinguishes them).

## Acceptance criteria

- With the cap set low in a test, rendering past it deletes the oldest renders and keeps the newest
- A deleted render is transparently re-rendered on the next request
- An in-progress render is never deleted
