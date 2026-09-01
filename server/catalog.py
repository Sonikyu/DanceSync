"""JSON-file metadata index for references and clips.

Kept separate from `storage.py`: this module never touches raw file bytes,
only the small records that describe them. Swapping local files for a real
database later means replacing this module alone.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from server.models import Clip, Reference


class Catalog:
    def __init__(self, root: Path):
        self.root = root

    def save_reference(self, reference: Reference) -> None:
        self._write("references", reference.id, reference)

    def get_reference(self, reference_id: str) -> Optional[Reference]:
        data = self._read("references", reference_id)
        return Reference.model_validate(data) if data else None

    def list_references(self) -> list[Reference]:
        return [Reference.model_validate(d) for d in self._list("references")]

    def save_clip(self, clip: Clip) -> None:
        self._write("clips", clip.id, clip)

    def get_clip(self, clip_id: str) -> Optional[Clip]:
        data = self._read("clips", clip_id)
        return Clip.model_validate(data) if data else None

    def list_clips(self) -> list[Clip]:
        return [Clip.model_validate(d) for d in self._list("clips")]

    def _write(self, kind: str, record_id: str, record: Reference | Clip) -> None:
        path = self._meta_path(kind, record_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(record.model_dump_json(indent=2))

    def _read(self, kind: str, record_id: str) -> Optional[dict]:
        path = self._meta_path(kind, record_id)
        return json.loads(path.read_text()) if path.exists() else None

    def _list(self, kind: str) -> list[dict]:
        dir_path = self.root / kind
        if not dir_path.exists():
            return []
        return [json.loads(p.read_text()) for p in sorted(dir_path.glob("*.json"))]

    def _meta_path(self, kind: str, record_id: str) -> Path:
        return self.root / kind / f"{record_id}.json"
