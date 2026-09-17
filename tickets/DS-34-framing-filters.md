# DS-34 — `dancesync/framing.py` filter builders

**Track:** Video editing · **Size:** S · **Depends on:** [DS-33](DS-33-edit-models-api.md) · **Spec:** [video-editing.md](../specs/video-editing.md)

## Context

Pure string builders in their own module, unit-tested without running ffmpeg. `sync.py` is 148 lines and would pass 200 if these went there.

## Scope

- Filters: rotate (`transpose=1` / `hflip,vflip` / `transpose=2`), crop (`crop=trunc(iw*W/2)*2:trunc(ih*H/2)*2:iw*X:ih*Y`), mirror (`hflip`).
- A fixed order — rotate, crop, mirror, scale — matching what the browser does in DS-37. The crop is stored un-mirrored, so turning mirror on flips the cropped picture and the dancer stays inside the crop.
- Even-dimension rounding, which `yuv420p` requires.

## Acceptance criteria

- Unit tests cover each edit and each combination, plus the rounding
- No ffmpeg process runs in these tests
