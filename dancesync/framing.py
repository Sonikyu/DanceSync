"""ffmpeg filters for the edits: each video's framing, and the take's trim.
Pure string builders: nothing here runs ffmpeg.

Framing is rotate, crop, mirror, always in that order. The browser previews
it with CSS in the same order (`framingStyle` in web/src/editing.js), so the
two must change together. The crop is stored un-mirrored and mirror comes
after it, so turning mirror on flips the cropped picture and the dancer
stays inside the crop.
"""

from __future__ import annotations

from dancesync.types import Crop, Framing, Trim

# Clockwise, like CSS rotate(): transpose=1 turns 90 degrees clockwise.
_ROTATE_FILTERS = {0: [], 90: ["transpose=1"], 180: ["hflip", "vflip"], 270: ["transpose=2"]}


def framing_filters(framing: Framing) -> list[str]:
    """The filters that frame one video, in order; empty when unedited."""
    filters = list(_ROTATE_FILTERS[framing.rotate])
    if framing.crop is not None:
        filters.append(crop_filter(framing.crop))
    if framing.mirror:
        filters.append("hflip")
    return filters


def crop_filter(crop: Crop) -> str:
    """Width and height round down to even pixels, which yuv420p needs, and
    never up, so a take-only render is never upscaled. `iw`/`ih` are the
    frame after rotation."""
    return (
        f"crop=trunc(iw*{crop.w:.6f}/2)*2:trunc(ih*{crop.h:.6f}/2)*2"
        f":iw*{crop.x:.6f}:ih*{crop.y:.6f}"
    )


def framing_chain(framing: Framing) -> str:
    """`framing_filters` as the start of a filter chain: each one followed
    by a comma, so the next filter can follow. Empty when unedited."""
    return "".join(f"{f}," for f in framing_filters(framing))


def trim_chain(trim: Trim | None, kind: str) -> str:
    """The start of the take's video (`kind` "") or audio (`kind` "a")
    chain that keeps only the trimmed stretch, in clip time and starting
    from zero. Empty when untrimmed."""
    if trim is None:
        return ""
    return f"{kind}trim=start={trim.start_sec:.6f}:end={trim.end_sec:.6f},{kind}setpts=PTS-STARTPTS,"
