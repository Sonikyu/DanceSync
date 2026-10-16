"""Local filesystem storage for uploaded media, keyed by content hash.

Kept separate from `catalog.py`'s metadata index: this module only ever
touches raw file bytes. A future cloud backend (S3/GCS) replaces this module
alone -- routes and the catalog never see a filesystem path directly.
"""

from __future__ import annotations

import hashlib
import shutil
import uuid
from pathlib import Path

from fastapi import UploadFile

_HASH_CHUNK = 1024 * 1024


class StorageError(RuntimeError):
    pass


class LocalStorage:
    def __init__(self, root: Path):
        self.root = root

    def save(self, kind: str, filename: str, upload: UploadFile, max_bytes: int) -> tuple[str, Path]:
        """Stream `upload` to disk, returning (content-hash id, saved path).

        Streamed rather than read into memory in one shot -- clips can be up
        to 500 MB of phone video. Two uploads with identical bytes land on the
        same id, so re-uploading a reference doesn't duplicate storage.
        """
        suffix = Path(filename).suffix.lower()
        kind_dir = self.root / kind
        kind_dir.mkdir(parents=True, exist_ok=True)
        tmp_path = kind_dir / f".tmp-{uuid.uuid4().hex}{suffix}"

        digest = hashlib.sha256()
        written = 0
        with open(tmp_path, "wb") as out:
            while chunk := upload.file.read(_HASH_CHUNK):
                written += len(chunk)
                if written > max_bytes:
                    tmp_path.unlink(missing_ok=True)
                    raise StorageError(f"upload exceeds {max_bytes} byte limit")
                digest.update(chunk)
                out.write(chunk)

        content_id = digest.hexdigest()[:32]
        final_path = kind_dir / f"{content_id}{suffix}"
        if final_path.exists():
            tmp_path.unlink()
        else:
            shutil.move(str(tmp_path), str(final_path))
        return content_id, final_path

    def save_file(self, kind: str, src_path: Path, filename: str) -> tuple[str, Path]:
        """Move an already-downloaded file into place, returning (content-hash
        id, saved path). `src_path` must be on the same filesystem, so the
        move is a rename."""
        digest = hashlib.sha256()
        with open(src_path, "rb") as src:
            while chunk := src.read(_HASH_CHUNK):
                digest.update(chunk)

        content_id = digest.hexdigest()[:32]
        final_path = self.path_for(kind, content_id, Path(filename).suffix.lower())
        final_path.parent.mkdir(parents=True, exist_ok=True)
        if not final_path.exists():
            src_path.replace(final_path)
        return content_id, final_path

    def path_for(self, kind: str, content_id: str, suffix: str) -> Path:
        return self.root / kind / f"{content_id}{suffix}"
