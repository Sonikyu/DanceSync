"""POST /api/references (upload) and GET /api/references (list)."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

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
    return catalog.list_references()
