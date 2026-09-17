# DS-02 — Fail fast when ffmpeg is missing

**Track:** Foundations · **Size:** XS · **Depends on:** nothing · **Spec:** [next-steps.md](../next-steps.md) Phase 5

## Context

ffmpeg is a hard runtime dependency for every decode and render, but a server started without it comes up fine and fails later, deep inside an upload, with an error the dancer can't act on.

## Scope

- `dancesync/ffmpeg.py` already has a presence check. Call it from a FastAPI lifespan startup handler in `server/main.py` and raise with an install hint (`brew install ffmpeg`) so the process exits.
- Include the resolved binary path and version in the startup log line.

## Acceptance criteria

- With ffmpeg off `PATH`, the server exits at startup with a message naming the fix
- With ffmpeg present, startup logs its version and serves normally
- A test asserts the startup check raises when the presence check reports missing
