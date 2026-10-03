"""POST /api/references (upload), POST /api/references/import (from a
YouTube link), GET /api/references (list), and GET /api/references/{id}/media
(the song file itself)."""

from __future__ import annotations

import tempfile
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
from fastapi.responses import FileResponse

from dancesync.audio import decode, duration_sec, is_supported
from server import youtube
from server.catalog import Catalog
from server.config import MAX_REFERENCE_BYTES
from server.deps import get_catalog, get_storage
from server.models import ImportRequest, Reference
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


@router.post("/import", response_model=Reference, status_code=201)
def import_reference(
    body: ImportRequest,
    response: Response,
    storage: LocalStorage = Depends(get_storage),
    catalog: Catalog = Depends(get_catalog),
) -> Reference:
    """Download a YouTube video into a new reference: 201, or 200 with the
    existing one when this video was imported before. Blocks until the
    download is done, as clip alignment does. A plain `def`, so FastAPI runs
    it in a thread and a minute-long download doesn't hold up other requests."""
    try:
        video_id = youtube.parse_video_id(body.url)
    except youtube.YouTubeError as exc:
        raise HTTPException(exc.status, str(exc)) from exc

    source_url = youtube.watch_url(video_id)
    existing = _imported_reference(catalog, source_url)
    if existing is not None:
        response.status_code = 200
        return existing
    if not youtube.is_installed():
        raise HTTPException(503, "yt-dlp is not installed on the server")

    try:
        reference = _download_reference(video_id, storage)
    except youtube.YouTubeError as exc:
        raise HTTPException(exc.status, str(exc)) from exc
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


def _imported_reference(catalog: Catalog, source_url: str) -> Reference | None:
    """Repeat imports are matched by video, not content hash: two downloads
    of one video aren't guaranteed to be byte-identical."""
    matches = [r for r in catalog.list_references() if r.source_url == source_url]
    return matches[0] if matches else None


def _download_reference(video_id: str, storage: LocalStorage) -> Reference:
    """Probe, download into a temp dir beside the media (so saving it is a
    rename), and describe it as a new reference. The id is still the content
    hash of the bytes, like an upload's."""
    info = youtube.probe(video_id)
    filename = youtube.safe_filename(info.title, video_id)
    storage.root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=storage.root, prefix=".import-") as tmp_dir:
        downloaded = youtube.download(video_id, Path(tmp_dir))
        reference_id, path = storage.save_file("references", downloaded, filename)

    return Reference(
        id=reference_id,
        filename=filename,
        duration_sec=duration_sec(decode(path)),
        created_at=datetime.now(timezone.utc),
        source_url=youtube.watch_url(video_id),
    )
