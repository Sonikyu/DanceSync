"""POST /api/clips/{id}/select -- record the user's chosen candidate -- and
PUT / DELETE /api/clips/{id}/manual -- an alignment set by hand."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException

from dancesync import audio
from server import config
from server.catalog import Catalog
from server.deps import get_catalog, get_storage
from server.models import Clip, ManualAlignment, SelectCandidateRequest
from server.storage import LocalStorage

router = APIRouter(prefix="/api/clips", tags=["clips"])


@router.post("/{clip_id}/select", response_model=Clip)
async def select_candidate(
    clip_id: str,
    body: SelectCandidateRequest,
    catalog: Catalog = Depends(get_catalog),
) -> Clip:
    """Picking a candidate also drops any manual alignment, which would
    otherwise keep overriding the pick."""
    clip = _clip_or_404(catalog, clip_id)
    if not 0 <= body.index < len(clip.alignment.top_candidates):
        raise HTTPException(400, f"index {body.index} out of range")

    clip.alignment.selected_index = body.index
    clip.alignment.manual = None
    catalog.save_clip(clip)
    return clip


@router.put("/{clip_id}/manual", response_model=Clip)
def set_manual_alignment(
    clip_id: str,
    body: ManualAlignment,
    storage: LocalStorage = Depends(get_storage),
    catalog: Catalog = Depends(get_catalog),
) -> Clip:
    """Override the matcher's alignment. The rate must be a playable practice
    speed, and the offset (original reference timeline) must leave some of
    the take over the song: no earlier than minus the take's length, no
    later than the song's end."""
    clip = _clip_or_404(catalog, clip_id)
    if not config.MIN_MANUAL_RATE <= body.rate <= config.MAX_MANUAL_RATE:
        raise HTTPException(422, f"rate must be {config.MIN_MANUAL_RATE}-{config.MAX_MANUAL_RATE}")
    min_offset_sec = -_clip_duration_sec(storage, clip)
    max_offset_sec = catalog.get_reference(clip.reference_id).duration_sec
    if not min_offset_sec <= body.offset_sec <= max_offset_sec:
        raise HTTPException(422, f"offset_sec must be {min_offset_sec:.2f} to {max_offset_sec:.2f}")

    clip.alignment.manual = body
    catalog.save_clip(clip)
    return clip


@router.delete("/{clip_id}/manual", response_model=Clip)
async def clear_manual_alignment(clip_id: str, catalog: Catalog = Depends(get_catalog)) -> Clip:
    """Back to automatic: the matcher's candidates were never touched."""
    clip = _clip_or_404(catalog, clip_id)
    clip.alignment.manual = None
    catalog.save_clip(clip)
    return clip


def _clip_or_404(catalog: Catalog, clip_id: str) -> Clip:
    clip = catalog.get_clip(clip_id)
    if clip is None:
        raise HTTPException(404, f"no clip with id {clip_id}")
    return clip


def _clip_duration_sec(storage: LocalStorage, clip: Clip) -> float:
    """From the decoded audio, which is cached from alignment."""
    clip_path = storage.path_for("clips", clip.id, Path(clip.filename).suffix.lower())
    return audio.duration_sec(audio.decode(clip_path))
