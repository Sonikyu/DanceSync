"""Server config: storage location, upload limits, CORS origins."""

from pathlib import Path

STORAGE_ROOT = Path(__file__).resolve().parent.parent / ".data" / "server"

MAX_REFERENCE_BYTES = 100 * 1024 * 1024
MAX_CLIP_BYTES = 500 * 1024 * 1024

ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:3000",
]
