"""POST /api/clips (upload + auto-align), GET /api/clips/{id}, and
GET /api/clips/{id}/media (the uploaded take itself)."""

from __future__ import annotations

from datetime import datetime, timezone
from math import isinf
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from dancesync.audio import is_supported
from dancesync.config import AMBIGUOUS_PEAK_RATIO, MIN_CLIP_SEC, MIN_MATCH_SCORE
from dancesync.types import Candidate as MatchCandidate
from server.catalog import Catalog
from server.config import MAX_CLIP_BYTES
from server.deps import get_catalog, get_storage
from server.models import AlignmentResult, Candidate, Clip
from server.storage import LocalStorage, StorageError
from server.worker import ClipTooShortError, align_clip

router = APIRouter(prefix="/api/clips", tags=["clips"])


@router.post("", response_model=Clip, status_code=201)
async def upload_clip(
    reference_id: str,
    file: UploadFile = File(...),
    storage: LocalStorage = Depends(get_storage),
    catalog: Catalog = Depends(get_catalog),
) -> Clip:
    reference = catalog.get_reference(reference_id)
    if reference is None:
        raise HTTPException(404, f"no reference with id {reference_id}")
    if not file.filename or not is_supported(Path(file.filename)):
        raise HTTPException(415, f"unsupported format: {file.filename}")

    try:
        clip_id, clip_path = storage.save("clips", file.filename, file, MAX_CLIP_BYTES)
    except StorageError as exc:
        raise HTTPException(413, str(exc)) from exc

    reference_suffix = Path(reference.filename).suffix.lower()
    reference_path = storage.path_for("references", reference.id, reference_suffix)
    try:
        match = align_clip(clip_path, reference_path, reference.id)
    except ClipTooShortError as exc:
        clip_path.unlink(missing_ok=True)
        raise HTTPException(422, _too_short_detail(exc.duration_sec)) from exc

    clip = Clip(
        id=clip_id,
        reference_id=reference.id,
        filename=file.filename,
        alignment=AlignmentResult(
            top_candidates=[_candidate_model(c) for c in match.top_candidates],
            ambiguous=match.peak_ratio < AMBIGUOUS_PEAK_RATIO,
            failed=match.score < MIN_MATCH_SCORE,
        ),
        created_at=datetime.now(timezone.utc),
    )
    catalog.save_clip(clip)
    return clip


@router.get("/{clip_id}", response_model=Clip)
async def get_clip(clip_id: str, catalog: Catalog = Depends(get_catalog)) -> Clip:
    clip = catalog.get_clip(clip_id)
    if clip is None:
        raise HTTPException(404, f"no clip with id {clip_id}")
    return clip


@router.get("/{clip_id}/media", response_class=FileResponse)
async def clip_media(
    clip_id: str,
    storage: LocalStorage = Depends(get_storage),
    catalog: Catalog = Depends(get_catalog),
) -> FileResponse:
    """The uploaded take, byte for byte, so the browser can play it sped up
    instead of waiting for a render. FileResponse answers byte-range
    requests, so a 500 MB take can be seeked without downloading it whole."""
    clip = catalog.get_clip(clip_id)
    if clip is None:
        raise HTTPException(404, f"no clip with id {clip_id}")
    return FileResponse(storage.path_for("clips", clip.id, Path(clip.filename).suffix.lower()))


def _too_short_detail(duration_sec: float) -> dict:
    """Structured, so the UI can word it for dancers with both numbers."""
    return {"error": "clip_too_short", "duration_sec": duration_sec, "min_sec": MIN_CLIP_SEC}


def _candidate_model(candidate: MatchCandidate) -> Candidate:
    """An infinite peak_ratio (no competing peak at all) becomes None, since
    JSON can't carry infinity."""
    peak_ratio = None if isinf(candidate.peak_ratio) else candidate.peak_ratio
    return Candidate(
        rate=candidate.rate,
        offset_sec=candidate.offset_sec,
        score=candidate.score,
        peak_ratio=peak_ratio,
    )
