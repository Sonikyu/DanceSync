# Follow one dancer

> TODO.md: "following certain dancer"

**Size:** L · **Depends on:**
- [video-editing](video-editing.md), for the crop plumbing in the preview and the render. Following a dancer is a crop that moves.
- Phase 5 background jobs. Tracking a 4-minute video takes minutes, too long for a request.

## Goal

In a group reference video, the user taps one dancer. The reference view then zooms in on that dancer and follows them through formation changes, in both the player and the downloads.

## Why a spike comes first

Finding people in each frame is a solved problem. Keeping track of the *same* person through a choreography is not. Dancers cross paths, block each other, wear matching outfits, and move fast, and those are exactly the moments when off-the-shelf trackers mix up who is who. As with alignment, prove it on real material before building any UI.

### Spike: go/no-go

- **Material:** at least 5 real group practice videos, with 4–9 dancers, some filmed on a fixed camera and some on a moving one, some in matching outfits and some not. For one dancer per video, hand-label a box every 2 s. A small labeling script is enough, at about 120 boxes per 4-minute video.
- **Pipeline:** detect people every Nth frame, run a multi-object tracker, take the track the user would tap, and turn it into a smoothed crop path.
- **Metrics:**
  - *Kept in frame:* the share of labeled moments where the dancer's box center falls inside the crop.
  - *Identity switches* per minute.
- **Gate:** at least 95% kept in frame, with no more than one manual correction per minute (see step 3 below), on the fixed-camera videos.
- **If the spike fails, ship a keyframed crop instead.** The user sets the crop at a few moments, and it moves linearly between them. It uses the same plumbing with no computer vision.

### Candidate stack (pick in the spike)

- **Detector:** a small YOLOX or RT-DETR model (Apache-2.0), exported to ONNX and run with `onnxruntime`. Ultralytics YOLO is the fastest way to try things, but it's AGPL-3.0, which matters if this code is ever published.
- **Tracker:** ByteTrack (MIT), which links detections across frames by box overlap and motion. Add appearance-based re-identification only if identity switches fail the gate.
- **MediaPipe's pose landmarker** (Apache-2.0) finds several people, but it doesn't assign track IDs, so it would still need a tracker.
- **Dependency cost:** `onnxruntime` plus a model file of tens of MB would make this the heaviest dependency in the project. The model file is gitignored, like media. The spike should show the result is worth it.

## Product design (if the spike passes)

1. **Track once per reference.** The first time someone asks to follow a dancer in a song, a background job tracks everyone in the reference video. It stores the tracks keyed by the reference's content hash, the same way stretched features are cached. Every later take, and every choice of dancer, reuses them.
2. **Pick.** A paused frame shows a box around each dancer, and the user taps one. The choice is saved on the Reference as `follow: {track_id, corrections: [(time_sec, track_id), …]}`.
3. **Correct.** When the view drifts onto the wrong dancer, the user pauses and taps the right one, which relinks the track from that moment on. This is the fix for identity switches, and the spike's gate counts it.
4. **Play and render.** The player and the downloads apply the same crop path.

### Crop path

- **The crop size stays fixed for the whole song.** It's the dancer's largest box times a margin of about 1.6, at the output aspect ratio. Only the position moves. A crop that resizes with the box makes the dancer seem to breathe in and out.
- **The center is smoothed,** because tracks jitter from frame to frame. Use a centered moving average over about 0.5 s, or a one-euro filter, and clamp the crop to the frame edges.
- **The path is sampled at 10 fps** and linearly interpolated between samples, in both the player and the render.
- **Path times are in original reference-timeline seconds.** The invariant holds here too.
- **The path is built with pure numpy** in `dancesync/follow.py`, so it can be unit-tested without video.

### Rendering and preview

- **Render:** ffmpeg's `crop` filter accepts `x` and `y` commands, so generate a `sendcmd` script from the path with one command per sample. No frames are decoded in Python. The spike should confirm the motion is smooth and fast enough.
- **Preview:** `requestVideoFrameCallback` on the reference `<video>` sets the transform from the path at `currentTime`. Where that callback isn't available, use `requestAnimationFrame`.

### What to build

```
dancesync/tracking.py      detect + track a video → tracks JSON (the only module that knows about the model)
dancesync/follow.py        tracks + pick + corrections → smoothed crop path
server/routes/follow.py    POST /api/references/{id}/tracks (start the job), GET (status + tracks), PUT …/follow
web/src/components/FollowPicker.jsx
```

## Performance

Detecting at 10 fps on a 4-minute, 30 fps video means about 2,400 detections. Expect a minute or two on an M-series CPU, but measure it in the spike. Tracking runs once per reference and is cached.

## Out of scope

- Following a dancer in the take. There's only one person in it, so a static crop does the job.
- Showing several dancers at once.
- Picking the dancer automatically.
