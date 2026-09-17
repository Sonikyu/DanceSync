# DS-14 — Progress over server-sent events

**Track:** Platform · **Size:** M · **Depends on:** [DS-13](DS-13-job-queue.md)

## Context

Polling tells the dancer that something is happening but not how far along it is. ffmpeg reports progress, and so does yt-dlp with `--newline`.

## Scope

- `GET /api/jobs/{id}/events`: an SSE stream of state and progress, ending on completion or failure.
- The worker publishes progress: ffmpeg's `-progress pipe:1` output for renders, and stage markers (decode, features, correlate) for alignment.
- A `useJobProgress` hook in the web app, with the existing spinners becoming progress bars. Falls back to polling when the stream drops.
- Document the proxy buffering setting SSE needs, in DS-12's runbook.

## Acceptance criteria

- A long render shows a progress bar that advances
- Killing the stream falls back to polling with no visible break
- Progress reaches 100% exactly when the file is ready to serve
