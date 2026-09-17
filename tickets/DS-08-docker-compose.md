# DS-08 — `docker compose up` starts the stack

**Track:** Ship (MVP) · **Size:** XS · **Depends on:** [DS-06](DS-06-dockerfile.md), [DS-07](DS-07-serve-web-dist.md)

## Scope

- A `docker-compose.yml` with the one service, a published port, and named volumes for the storage root and the feature cache.
- A `.env.example` with the settings worth changing: port, storage root, upload limits, CORS origins.
- README instructions: the three commands to a running app on a fresh machine.

## Acceptance criteria

- On a machine with only Docker installed, `docker compose up` reaches a working app
- Uploads and renders survive `docker compose down && up`
