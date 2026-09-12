"""GET /api/clips/{id}/synced -- the practice video re-timed to original speed."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from dancesync.sync import SyncError
from server.catalog import Catalog
from server.deps import get_catalog, get_storage
from server.models import Candidate, Clip
from server.storage import LocalStorage
from server.worker import sync_clip

router = APIRouter(prefix="/api/clips", tags=["clips"])


# A plain `def`, not `async def`: FastAPI runs it in a worker thread, so a
# render in progress doesn't stall every other request.
@router.get("/{clip_id}/synced", response_class=FileResponse)
def download_synced(
    clip_id: str,
    storage: LocalStorage = Depends(get_storage),
    catalog: Catalog = Depends(get_catalog),
) -> FileResponse:
    clip = catalog.get_clip(clip_id)
    if clip is None:
        raise HTTPException(404, f"no clip with id {clip_id}")
    reference = catalog.get_reference(clip.reference_id)
    if reference is None:
        raise HTTPException(404, f"no reference with id {clip.reference_id}")

    candidate = _chosen_candidate(clip)
    clip_path = storage.path_for("clips", clip.id, Path(clip.filename).suffix.lower())
    reference_suffix = Path(reference.filename).suffix.lower()
    reference_path = storage.path_for("references", reference.id, reference_suffix)
    out_path = storage.path_for("synced", _synced_id(clip, candidate), ".mp4")

    try:
        sync_clip(clip_path, reference_path, candidate.rate, candidate.offset_sec, out_path)
    except SyncError as exc:
        raise HTTPException(422, str(exc)) from exc

    download_name = f"{Path(clip.filename).stem}-synced.mp4"
    return FileResponse(out_path, media_type="video/mp4", filename=download_name)


def _chosen_candidate(clip: Clip) -> Candidate:
    """The user's pick if they made one, else the matcher's best guess."""
    index = clip.alignment.selected_index
    return clip.alignment.top_candidates[0 if index is None else index]


def _synced_id(clip: Clip, candidate: Candidate) -> str:
    """Name the render after everything it depends on -- clip bytes, reference
    bytes, and the chosen alignment -- so a cached file is never stale, even if
    the same clip is later re-uploaded against a different reference."""
    offset_ms = round(candidate.offset_sec * 1000)
    return f"{clip.id}-{clip.reference_id}-{candidate.rate}x-{offset_ms}ms"
