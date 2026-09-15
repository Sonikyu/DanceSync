"""GET /api/clips/{id}/synced -- the practice video re-timed to original speed,
alone or side by side with the reference video, under the song or under the
phone's own recording."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from dancesync.ffmpeg import SyncError
from dancesync.sync import Sound
from server.catalog import Catalog
from server.deps import get_catalog, get_storage
from server.models import Candidate, Clip, Layout
from server.storage import LocalStorage
from server.worker import sync_clip

router = APIRouter(prefix="/api/clips", tags=["clips"])


# A plain `def`, not `async def`: FastAPI runs it in a worker thread, so a
# render in progress doesn't stall every other request.
#
# HEAD renders exactly like GET but sends no body. The UI waits on a HEAD
# before showing the player, because iOS Safari won't fetch a <video> source
# until the user presses play -- so the render would never start.
@router.api_route("/{clip_id}/synced", methods=["GET", "HEAD"], response_class=FileResponse)
def download_synced(
    clip_id: str,
    sound: Sound = "song",
    layout: Layout = "take",
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
    out_path = storage.path_for("synced", _synced_id(clip, candidate, sound, layout), ".mp4")

    try:
        sync_clip(
            clip_path, reference_path, candidate.rate, candidate.offset_sec, out_path,
            sound=sound, layout=layout,
        )
    except SyncError as exc:
        raise HTTPException(422, str(exc)) from exc

    return FileResponse(out_path, media_type="video/mp4", filename=_download_name(clip, sound, layout))


def _chosen_candidate(clip: Clip) -> Candidate:
    """The user's pick if they made one, else the matcher's best guess."""
    index = clip.alignment.selected_index
    return clip.alignment.top_candidates[0 if index is None else index]


def _synced_id(clip: Clip, candidate: Candidate, sound: Sound, layout: Layout) -> str:
    """Name the render after everything it depends on -- clip bytes, reference
    bytes, the chosen alignment, and which render -- so a cached file is never
    stale, even if the same clip is later re-uploaded against a different reference."""
    offset_ms = round(candidate.offset_sec * 1000)
    return f"{clip.id}-{clip.reference_id}-{candidate.rate}x-{offset_ms}ms-{layout}-{sound}"


def _download_name(clip: Clip, sound: Sound, layout: Layout) -> str:
    """practice-synced.mp4, practice-side-by-side-room.mp4, and so on."""
    kind = "synced" if layout == "take" else "side-by-side"
    sound_suffix = "" if sound == "song" else f"-{sound}"
    return f"{Path(clip.filename).stem}-{kind}{sound_suffix}.mp4"
