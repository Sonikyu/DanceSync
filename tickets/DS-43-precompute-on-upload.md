# DS-43 — Stretch the reference when the song is uploaded

**Track:** Practice speeds · **Size:** S · **Depends on:** [DS-13](DS-13-job-queue.md), [DS-41](DS-41-incremental-feature-cache.md) · **Spec:** [practice-speeds.md](../specs/practice-speeds.md)

## Context

With 11 rates, the first take against a new song would wait minutes. But the dancer uploads the song before they film, so that work can run while they're filming and uploading.

## Scope

- Enqueue the stretch job on reference upload, on the job queue from DS-13.
- A clip upload that arrives before the job finishes waits for it rather than duplicating the work.

## Acceptance criteria

- Uploading a song then a take a few minutes later shows no stretch wait
- Uploading a take immediately after the song still succeeds, just slower
- The two paths never stretch the same rate twice concurrently
