"""POST /api/references (upload), GET /api/references (list), and
GET /api/references/{id}/media (the song file itself)."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from dancesync.audio import decode, duration_sec, is_supported
from server.catalog import Catalog
from server.config import MAX_REFERENCE_BYTES
from server.deps import get_catalog, get_storage
from server.models import Reference
from server.storage import LocalStorage, StorageError

router = APIRouter(prefix="/api/references", tags=["references"])


@router.post("", response_model=Reference, status_code=201)
async def upload_reference(
    file: UploadFile = File(...),
    storage: LocalStorage = Depends(get_storage),
    catalog: Catalog = Depends(get_catalog),
) -> Reference:
    if not file.filename or not is_supported(Path(file.filename)):
        raise HTTPException(415, f"unsupported format: {file.filename}")

    try:
        reference_id, path = storage.save("references", file.filename, file, MAX_REFERENCE_BYTES)
    except StorageError as exc:
        raise HTTPException(413, str(exc)) from exc

    existing = catalog.get_reference(reference_id)
    if existing is not None:
        return existing

    reference = Reference(
        id=reference_id,
        filename=file.filename,
        duration_sec=duration_sec(decode(path)),
        created_at=datetime.now(timezone.utc),
    )
    catalog.save_reference(reference)
    return reference


@router.get("", response_model=list[Reference])
async def list_references(catalog: Catalog = Depends(get_catalog)) -> list[Reference]:
    """Newest first -- the catalog's own order is by content hash, which means nothing to a person."""
    return sorted(catalog.list_references(), key=lambda r: r.created_at, reverse=True)


@router.get("/{reference_id}/media", response_class=FileResponse)
async def reference_media(
    reference_id: str,
    storage: LocalStorage = Depends(get_storage),
    catalog: Catalog = Depends(get_catalog),
) -> FileResponse:
    """The uploaded song file itself: audio for the candidate previews, and
    the choreography shown beside the take when the song file has video.
    FileResponse answers byte-range requests, so the browser can seek straight
    to an offset without downloading the whole file first."""
    reference = catalog.get_reference(reference_id)
    if reference is None:
        raise HTTPException(404, f"no reference with id {reference_id}")
    suffix = Path(reference.filename).suffix.lower()
    return FileResponse(storage.path_for("references", reference.id, suffix))
