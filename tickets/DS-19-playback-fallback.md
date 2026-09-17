# DS-19 — Fall back to the server render

**Track:** Instant preview · **Size:** S–M · **Depends on:** [DS-18](DS-18-play-raw-clip.md) · **Spec:** [instant-preview.md](../specs/instant-preview.md)

## Context

Some clips won't play in some browsers. HEVC is the iPhone default and support varies by browser and OS; `.avi`, `.mkv`, and `.3gp` rarely play at all. The rendered path stays regardless, because it's how downloads are made, so it's also the fallback.

## Scope

- On an `error` from the raw clip element, switch to today's path: render the take and play it at rate 1, with no action from the user beyond the wait.
- iOS Safari only lets an element play unmuted if a user gesture started it. The play handler must call `play()` on the sound-making element even during a negative-offset lead-in, then pause it immediately so `timeupdate` can start it later.
- A manual browser matrix recorded in the PR: Chrome, Safari, iOS Safari × {song, room} × {positive, negative offset} × {reference with video, without}. iOS must be a real device.

## Acceptance criteria

- An HEVC clip that Chrome refuses falls back and plays, with a brief "Preparing…" state
- Unmuted playback works on a real iPhone for both sounds, including a negative offset
- The matrix is in the PR description with the device and OS versions named
