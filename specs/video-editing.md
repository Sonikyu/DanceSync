# Basic video editing: crop, mirror, rotate, trim

> TODO.md: "super basic video editing (to get the right size)(dance practice videos are different resolution)"

**Size:** M · **Depends on:** [instant-preview](instant-preview.md). With it, edits appear in the preview immediately and cost a render only on download. · **Unblocks:** [follow-dancer](follow-dancer.md)

## Problem

Reference practice videos are usually landscape, often with a whole group across the frame. Phone takes are usually portrait, with the dancer small in the middle of a room. Side by side, the two dancers come out at very different sizes. Takes also often start and end with walking to the phone, some come out sideways, and many dancers learn from a mirrored reference.

## Goal

Each video gets an **Adjust** mode on Watch. Edits apply live in the player (CSS) and in the download (ffmpeg).

| edit                     | reference | take | stored on                            |
|--------------------------|-----------|------|--------------------------------------|
| crop                     | ✓         | ✓    | `Reference.framing` / `Clip.framing` |
| mirror                   | ✓         | ✓    | same                                 |
| rotate 90° / 180° / 270° | ✓         | ✓    | same                                 |
| trim start / end         |           | ✓    | `Clip.trim`                          |

The reference's framing is stored on the Reference, so it's set once per song and reused for every take. The take's edits are stored on the Clip.

## Data model

```python
class Crop(BaseModel):
    """Fractions of the rotated, un-mirrored frame: 0..1, origin top-left."""
    x: float
    y: float
    w: float
    h: float

class Framing(BaseModel):
    rotate: Literal[0, 90, 180, 270] = 0
    crop: Crop | None = None
    mirror: bool = False

class Trim(BaseModel):
    """Seconds in the ORIGINAL uploaded clip, before re-timing."""
    start_sec: float
    end_sec: float
```

`Reference` gets `framing: Framing = Framing()`. `Clip` gets `framing` and `trim: Trim | None = None`. Because of the defaults, existing catalog JSON loads unchanged.

## Key decisions

- **The browser and ffmpeg apply edits in the same order: rotate, crop, mirror, scale.** The crop is stored in un-mirrored coordinates, so turning mirror on flips the cropped picture and the dancer stays inside the crop. When the user draws a crop on a mirrored preview, the editor converts it with `x = 1 - x_drawn - w`.
- **Trimming the start moves where the output begins in the song. Compute that shift in exactly one place.** Trimming `start_sec` means the output begins at clip time `start_sec`, and that moment heard reference time `offset_sec + start_sec × rate`.
  - Add one helper, `trimmed_offset(offset_sec, rate, trim_start_sec)`, to `dancesync/sync.py`, with a matching function in `flow.js`.
  - Never write the shifted value back into `AlignmentResult`. The matched offset stays the offset of the clip's first sample.
  - The output lasts `(end_sec - start_sec) × rate`.
  - This is the kind of bug the original-timeline invariant exists to catch, so it gets its own tests.
- **Trim changes only the output.** Alignment still runs on the whole clip, because more audio gives a better match.
- **Rotation is a manual override.** ffmpeg and browsers already honor the phone's rotation metadata. Rotate is only for footage whose metadata is wrong, such as a phone lying flat.
- **`MIN_CROP_FRAC = 0.2`** (in config) is the smallest crop allowed in each dimension. A tighter crop of a 1080p frame gets upscaled more than about 3× in the 720p compare render and turns to mush.
- **Take-only renders keep the cropped resolution** with no upscaling. Width and height are rounded down to even numbers.
- **The browser preview uses CSS transforms, not `object-view-box`**, which Safari lacks. Each `<video>` sits in a wrapper that has `overflow: hidden` and the crop's aspect ratio. A pure function in `flow.js`, `framingStyle(framing, videoWidth, videoHeight)`, returns the transform and has unit tests.
- **The filter strings get their own module,** `dancesync/framing.py`: pure string builders, unit-tested without running ffmpeg. `sync.py` is 148 lines now and would pass 200 if they went there.

## Cache invariant

A render's filename must name everything the render depends on. Add a short hash of `(reference.framing, clip.framing, clip.trim)` as a field of `RenderParams` (DS-03), or the server will serve a cached render with the old edits.

**The browser also caches by URL,** so the same field goes in `RENDER_PARAM_FIELDS` in `api.js` and in `flow.renderParams`. `tests/test_render_params.py` fails if the field is on one side only, which is the bug this feature is most likely to ship with.

## ffmpeg

| edit                   | filter |
|------------------------|--------|
| rotate 90 / 180 / 270  | `transpose=1` / `hflip,vflip` / `transpose=2` |
| crop                   | `crop=trunc(iw*W/2)*2:trunc(ih*H/2)*2:iw*X:ih*Y` |
| mirror                 | `hflip` |
| trim (take)            | `trim=start=S:end=E,setpts=PTS-STARTPTS` in clip time, before re-timing; `atrim` on room audio; the reference cut moved by `trimmed_offset` |

In compare renders, both videos' edit chains run before the fit `scale`.

## UI

- **Adjust** under each video pauses playback and shows that video with a crop box that can be dragged and resized. It uses pointer events, so touch works. **Mirror** and **Rotate** buttons sit next to it.
- **Trim** (take only) is two buttons, **Set start here** and **Set end here**, that use the current play position. They're easier on a phone than two handles on a scrubber.
- **Reset** clears the edits. **Done** saves them with a `PUT`.

## API

```
PUT /api/references/{id}/framing   body: Framing          → Reference
PUT /api/clips/{id}/edits          body: {framing, trim}  → Clip
```

The server validates the crop (inside 0..1 and at least `MIN_CROP_FRAC`) and the trim (`0 ≤ start < end ≤ clip duration`).

## Tests

- `framing.py`: filter strings for each edit and each combination; rounding to even dimensions.
- `trimmed_offset`: with a trim, the rendered audio still lines up. Reuse `test_sync.py`'s approach of rendering a synthetic clip and checking where the reference audio lands.
- Render dimensions after crop and rotate, checked with ffprobe.
- API: the PUT endpoints, their validation errors, and a changed edit producing a different `render_cache_id`.
- `flow.test.js`: `framingStyle`, the mirrored-crop conversion, and time mapping with a trim.

## Acceptance criteria

- After cropping a group reference down to one dancer and a portrait take down to the dancer, the two appear at a similar size side by side
- Every edit looks the same in the preview and the download
- A trimmed take stays in sync with the song from its new first frame
- No edit forces a re-align

## Out of scope

Crops that move over time (that's [follow-dancer](follow-dancer.md)), color and filters, cutting out the middle of a take, and a different reference framing for each take.
