"""POST /api/clips (upload + auto-align) and GET /api/clips/{id}."""

from __future__ import annotations

from datetime import datetime, timezone
from math import isinf
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from dancesync.audio import is_supported
from dancesync.config import AMBIGUOUS_PEAK_RATIO
from dancesync.types import Candidate as MatchCandidate
from server.catalog import Catalog
from server.config import MAX_CLIP_BYTES
from server.deps import get_catalog, get_storage
from server.models import AlignmentResult, Candidate, Clip
from server.storage import LocalStorage, StorageError
from server.worker import align_clip

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
    match = align_clip(clip_path, reference_path, reference.id)

    clip = Clip(
        id=clip_id,
        reference_id=reference.id,
        filename=file.filename,
        alignment=AlignmentResult(
            top_candidates=[_candidate_model(c) for c in match.top_candidates],
            ambiguous=match.peak_ratio < AMBIGUOUS_PEAK_RATIO,
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
