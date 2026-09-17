# DS-18 — Play the raw clip instead of a render

**Track:** Instant preview · **Size:** M · **Depends on:** [DS-15](DS-15-clip-media-endpoint.md), [DS-16](DS-16-clip-time-mapping.md), [DS-17](DS-17-leader-follower-by-sound.md) · **Spec:** [instant-preview.md](../specs/instant-preview.md)

## Context

This is the payoff: the Watch screen plays as soon as alignment finishes, and ffmpeg runs only on Download.

## Scope

- `ComparePlayer.jsx` sources `/api/clips/{id}/media` and applies `playbackRate = 1 / rate` to it, with the reference at `offset_sec + T`.
- `WatchStep.jsx` renders nothing on mount; status starts at "ready". The two download buttons keep their existing HEAD-then-download behaviour and become the only thing that triggers a render.
- Edge cases from the spec: the take running past the end of the song, an audio-only reference (element hidden but playing), and changing the match updating rate and offset without reloading media.

## Out of scope

The unplayable-clip fallback (DS-19), and background prefetch of the download render — deliberately not in v1.

## Acceptance criteria

- For a 60 s 1080p clip, Watch can play within a couple of seconds of alignment finishing
- On the same clap or count, dancer and song line up as well as in the rendered download
- Download still produces the same file it does today
