"""PUT /api/references/{id}/framing -- how the song's video is shown under
every take -- and PUT /api/clips/{id}/edits -- the take's framing and trim.
Edits change only what renders show, so neither re-aligns anything."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException

from dancesync.types import Framing, Trim
from server import config
from server.catalog import Catalog
from server.deps import get_catalog, get_storage
from server.models import Clip, ClipEdits, Reference
from server.storage import LocalStorage
from server.worker import clip_duration_sec

router = APIRouter(prefix="/api", tags=["edits"])

# Float noise from the browser's arithmetic: 0.8 + 0.2 can come out a hair over 1.
_TOLERANCE = 1e-9


@router.put("/references/{reference_id}/framing", response_model=Reference)
async def set_reference_framing(
    reference_id: str,
    body: Framing,
    catalog: Catalog = Depends(get_catalog),
) -> Reference:
    reference = catalog.get_reference(reference_id)
    if reference is None:
        raise HTTPException(404, f"no reference with id {reference_id}")
    _check_framing(body)

    reference.framing = body
    catalog.save_reference(reference)
    return reference


@router.put("/clips/{clip_id}/edits", response_model=Clip)
def set_clip_edits(
    clip_id: str,
    body: ClipEdits,
    storage: LocalStorage = Depends(get_storage),
    catalog: Catalog = Depends(get_catalog),
) -> Clip:
    clip = catalog.get_clip(clip_id)
    if clip is None:
        raise HTTPException(404, f"no clip with id {clip_id}")
    _check_framing(body.framing)
    if body.trim is not None:
        clip_path = storage.path_for("clips", clip.id, Path(clip.filename).suffix.lower())
        _check_trim(body.trim, clip_duration_sec(clip_path))

    clip.framing = body.framing
    clip.trim = body.trim
    catalog.save_clip(clip)
    return clip


def _check_framing(framing: Framing) -> None:
    """The crop must lie inside the frame and keep at least MIN_CROP_FRAC of it each way."""
    crop = framing.crop
    if crop is None:
        return
    if min(crop.x, crop.y) < 0 or max(crop.x + crop.w, crop.y + crop.h) > 1 + _TOLERANCE:
        raise HTTPException(422, "crop must lie inside the frame (0 to 1)")
    if min(crop.w, crop.h) < config.MIN_CROP_FRAC - _TOLERANCE:
        raise HTTPException(422, f"crop must be at least {config.MIN_CROP_FRAC} of the frame each way")


def _check_trim(trim: Trim, duration_sec: float) -> None:
    """0 <= start < end <= the take's length, in the take's own seconds."""
    if not 0 <= trim.start_sec < trim.end_sec <= duration_sec + config.TRIM_END_SLACK_SEC:
        raise HTTPException(422, f"trim must satisfy 0 <= start_sec < end_sec <= {duration_sec:.2f}")
