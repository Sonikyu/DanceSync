# DS-06 — Dockerfile with ffmpeg and the Python dependencies

**Track:** Ship (MVP) · **Size:** S · **Depends on:** nothing · **Spec:** [next-steps.md](../next-steps.md) Phase 5

## Context

One-command run is an MVP item. This is the first of its three tickets.

## Scope

- A multi-stage Dockerfile: a Node stage that builds `web/dist`, and a Python 3.11 slim runtime stage with ffmpeg installed and the package installed from `pyproject.toml`.
- Storage root and cache dir as volumes, so uploads and renders survive a rebuild.
- `uvicorn server.main:app` as the entrypoint, port configurable by env var.
- A `.dockerignore` that excludes `.data/`, `.cache/`, `spike/data/`, and `node_modules`.

## Acceptance criteria

- `docker build` produces an image that starts and answers `GET /api/references`
- ffmpeg is present in the image and DS-02's startup check passes
- The built image does not contain any media from `.data/`
