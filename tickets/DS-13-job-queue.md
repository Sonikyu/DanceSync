# DS-13 — Move align and render onto a job queue

**Track:** Platform · **Size:** M–L · **Depends on:** nothing · **Unblocks:** [DS-14](DS-14-progress-events.md), [DS-43](DS-43-precompute-on-upload.md), [DS-46](DS-46-follow-dancer-spike.md)

## Context

Alignment runs inside the POST and rendering inside the GET. That's fine at 10–30 s and fails at minutes: a reverse proxy times out at 60 s by default, and dancer tracking takes minutes.

## Scope

- An in-process job queue with a small worker pool — no Redis, no Celery. A job has an id, a kind, a state, a result, and an error.
- `POST /api/clips` enqueues alignment and returns the clip with a job id; `GET /api/clips/{id}` reports job state.
- `/synced` enqueues a render and returns 202 with a job id when the file isn't cached, instead of blocking.
- The web app polls job state where it used to block. Polling is replaced by SSE in DS-14.
- Jobs are in memory: a restart loses queued work, and the client re-requests. Say so in the code.

## Out of scope

Progress percentages and SSE (DS-14), persistence across restarts, multi-process workers.

## Acceptance criteria

- Uploading a clip returns promptly and the UI shows alignment running
- A render longer than any proxy timeout completes and is served on the next request
- Two clips uploaded at once both complete
- The existing API tests pass against the queued path
