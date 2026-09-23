"""Serve the built web app from the API's own origin, so production needs no
CORS and no proxy in front of Vite, just like dev.

Registered after the API routers, so `/api/*` always wins. A path that looks
like a page (no file extension) gets `index.html`, so a reload on a deep link
works. A missing file (`/assets/old-hash.js`) is a 404, not HTML.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse


def mount_web_app(app: FastAPI, dist_dir: Path) -> None:
    """Add the catch-all route. Does nothing when there's no build, so the
    dev setup (Vite on :5173) is unchanged."""
    if not (dist_dir / "index.html").is_file():
        return

    root = dist_dir.resolve()

    @app.get("/{path:path}", include_in_schema=False)
    def web_app(path: str) -> FileResponse:
        if path == "api" or path.startswith("api/"):
            raise HTTPException(404, "Not Found")
        built_file = (root / path).resolve()
        if built_file.is_file() and built_file.is_relative_to(root):
            return FileResponse(built_file)
        if Path(path).suffix:
            raise HTTPException(404, "Not Found")
        return FileResponse(root / "index.html")
