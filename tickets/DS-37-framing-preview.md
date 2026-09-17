# DS-37 — Live edit preview with CSS transforms

**Track:** Video editing · **Size:** S · **Depends on:** [DS-18](DS-18-play-raw-clip.md), [DS-33](DS-33-edit-models-api.md) · **Spec:** [video-editing.md](../specs/video-editing.md)

## Context

`object-view-box` would be the natural tool, but Safari lacks it. Each `<video>` sits in a wrapper with `overflow: hidden` and the crop's aspect ratio instead.

## Scope

- `framingStyle(framing, videoWidth, videoHeight)` in `flow.js`, returning the transform, with unit tests.
- Wrapper elements and CSS in `styles.css`.
- The same order as ffmpeg: rotate, crop, mirror, scale.

## Acceptance criteria

- A crop, a rotation, and a mirror each look in the browser exactly as they come out of the render
- `flow.test.js` covers `framingStyle` and the mirrored-crop coordinate conversion
