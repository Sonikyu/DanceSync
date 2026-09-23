"""Keep the render directory under a size cap, least recently used first.

"Recently used" is the file's mtime: set when ffmpeg writes it, and bumped by
`touch` every time it's served. Renders are the only thing that grows the
directory, so the sweep runs after each new render rather than on a timer.
A deleted render is simply rendered again on its next request.
"""

from __future__ import annotations

import os
from pathlib import Path

# ffmpeg.run_to_file writes here first and renames on success.
_IN_PROGRESS_PREFIX = ".tmp-"


def touch(render_path: Path) -> None:
    os.utime(render_path)


def sweep(render_dir: Path, max_bytes: int, keep: Path) -> list[Path]:
    """Delete the least recently used finished renders until the directory's
    finished renders total at most `max_bytes`. Never deletes `keep` (the
    render about to be served) or a render still being written. Returns what
    it deleted, oldest first."""
    renders = sorted(_finished_renders(render_dir), key=lambda p: p.stat().st_mtime_ns)
    total_bytes = sum(p.stat().st_size for p in renders)
    deleted = []
    for render_path in renders:
        if total_bytes <= max_bytes:
            break
        if render_path == keep:
            continue
        total_bytes -= render_path.stat().st_size
        render_path.unlink(missing_ok=True)
        deleted.append(render_path)
    return deleted


def _finished_renders(render_dir: Path) -> list[Path]:
    if not render_dir.is_dir():
        return []
    return [
        p for p in render_dir.iterdir()
        if p.is_file() and not p.name.startswith(_IN_PROGRESS_PREFIX)
    ]
