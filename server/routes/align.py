"""POST /api/clips/{id}/select -- record the user's chosen candidate."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from server.catalog import Catalog
from server.deps import get_catalog
from server.models import Clip, SelectCandidateRequest

router = APIRouter(prefix="/api/clips", tags=["clips"])


@router.post("/{clip_id}/select", response_model=Clip)
async def select_candidate(
    clip_id: str,
    body: SelectCandidateRequest,
    catalog: Catalog = Depends(get_catalog),
) -> Clip:
    clip = catalog.get_clip(clip_id)
    if clip is None:
        raise HTTPException(404, f"no clip with id {clip_id}")
    if not 0 <= body.index < len(clip.alignment.top_candidates):
        raise HTTPException(400, f"index {body.index} out of range")

    clip.alignment.selected_index = body.index
    catalog.save_clip(clip)
    return clip
