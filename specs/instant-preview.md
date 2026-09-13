# Instant preview

> TODO.md: "just show the video side by side first and create later if download (to speed it up)"

**Size:** M · **Depends on:** nothing · **Unblocks:** [review-speed](review-speed.md), [layouts](layouts.md), [video-editing](video-editing.md). After this lands, each of those needs only preview-side changes plus the one download render.

## Problem

`WatchStep` asks the server to render two full videos (the take under the song, and the take under the room sound) and shows nothing until the song render is done. Each render takes about as long as the clip. The dancer waits through that on every take, even when they only want to watch and never download. Every later feature (layout, crop, speed) would add another render in front of the player.

## Goal

The Watch screen plays as soon as alignment finishes. The browser plays the **original uploaded clip**, sped up to full tempo, next to the reference, with no server render. ffmpeg runs only when the user presses Download.

## Timing

This is the same timing as `dancesync/sync.py`, expressed as playback rates. `T` is output time, the time the play bar shows (0 … clip duration × rate):

| element   | `currentTime` at output time T | `playbackRate` |
|-----------|--------------------------------|----------------|
| raw clip  | `T / rate`                     | `1 / rate` (a 0.75× take plays at 1.333) |
| reference | `offset_sec + T`               | `1`            |

- **Song sound:** the reference element makes the sound, and the clip is muted.
- **Room sound:** the clip makes the sound, and the reference is muted. When `playbackRate ≠ 1`, browsers keep the pitch by default, just as `atempo` does in the render.

The two conversions go in `flow.js` beside `referenceTimeFor`, as pure functions with unit tests. They're the frontend's equivalent of `frames_to_sec`: one place for the conversion.

## Key decisions

- **The element making the sound is the clock, and the muted one follows it.** Today `useLinkedPlayback` always treats the take as the clock and nudges the reference's `playbackRate` by up to ±10%. You can hear audio being nudged (a warble, and jumps when it has to seek), but you can't see a muted video being nudged. So the Sound toggle also decides which element leads. During the lead-in of a negative offset there's no song yet, so the clip leads until the song starts.
- **Switching sound flips mute instead of swapping `src`.** That makes the switch instant, and the `resumeRef` save-and-restore logic in `ComparePlayer` goes away.
- **Download renders on demand.** `DownloadButton` already sends a HEAD request and shows "Preparing…", so it becomes the only thing that triggers a render. v1 has no background prefetch: on a single-box server, rendering something nobody downloads wastes CPU. If the download wait feels long, revisit this.
- **Fall back to the server render.** Some clips won't play in some browsers: HEVC (the iPhone default) support varies by browser and OS, and `.avi`, `.mkv`, and `.3gp` rarely play. If the raw clip fires `error`, switch to today's path: render the take and play it at rate 1. That path stays regardless, because it's also how a download is made.
- **iOS Safari lets an element play unmuted only if a user gesture started it.** So the play-button handler must call `play()` on the sound-making element even during a negative-offset lead-in, then pause it right away. That lets `timeupdate` start it later. Test this on a real iPhone.

## What to build

```
server/routes/clips.py     GET /api/clips/{id}/media: the uploaded clip bytes (same shape as references' /media)
web/src/flow.js            clipTimeFor(outputSec, rate), outputTimeFor(clipSec, rate), plus tests
web/src/components/
  useLinkedPlayback.js     leader and follower chosen by `sound`; the follower is always muted
  ComparePlayer.jsx        plays the clip media instead of the synced render; falls back on error
  WatchStep.jsx            no render on mount; status starts at "ready"
```

`FileResponse` already answers range requests. The browser needs those to seek into a 500 MB clip without downloading all of it.

## Edge cases

- **Negative offset** (the phone started recording first): the reference holds its first frame until `T = -offset_sec`.
- **The take runs past the end of the song:** with room sound, playback carries on. With song sound, it goes silent, the same as the render's `apad`.
- **Audio-only reference:** the reference element stays hidden but still plays the song.
- **Change match:** the rate and offset change, but no media reloads.

## Tests

- `flow.test.js`: time-mapping round trips at rates 1, 0.75, and 0.5, including negative offsets; which element leads for each sound.
- `tests/test_api.py`: `/api/clips/{id}/media` returns the bytes, returns 404 for an unknown id, and answers `Range` with 206.
- A manual matrix, recorded in the PR: Chrome, Safari, and iOS Safari × {song, room} × {positive, negative offset} × {reference with video, without video}.

## Acceptance criteria

- For a 60 s 1080p clip, the Watch screen can play within a couple of seconds of alignment finishing
- On the same clap or count, the dancer and the song line up in the browser as well as they do in the rendered download
- Download produces the same file it does today
- A clip the browser can't play falls back to the render with no action from the user
