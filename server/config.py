"""Server config: storage location, upload limits, CORS origins, and where the
built web app lives. Each one can be overridden by a DANCESYNC_* environment
variable, which is how the Docker image points them at its volumes."""

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

STORAGE_ROOT = Path(os.environ.get("DANCESYNC_STORAGE_ROOT", ROOT / ".data" / "server"))

MAX_REFERENCE_BYTES = int(os.environ.get("DANCESYNC_MAX_REFERENCE_MB", 100)) * 1024 * 1024
MAX_CLIP_BYTES = int(os.environ.get("DANCESYNC_MAX_CLIP_MB", 500)) * 1024 * 1024

# Only needed when the web app is served from a different origin than the
# API. The Vite dev proxy and the built app served by FastAPI both avoid that.
ALLOWED_ORIGINS = os.environ.get(
    "DANCESYNC_CORS_ORIGINS", "http://localhost:5173,http://localhost:3000"
).split(",")

# Rendered videos are deleted least recently used first once they total more
# than this. Each one is a cache: deleting it only costs a re-render.
RENDER_CACHE_MAX_BYTES = int(float(os.environ.get("DANCESYNC_RENDER_CACHE_GB", 5)) * 1024**3)

# The output of `npm --prefix web run build`. Served at / when it exists.
WEB_DIST = Path(os.environ.get("DANCESYNC_WEB_DIST", ROOT / "web" / "dist"))

# One shared passphrase for the owner and friends. Unset means no sign-in at
# all, which is right for a laptop and wrong for anything on the internet.
PASSPHRASE = os.environ.get("DANCESYNC_PASSPHRASE") or None
SESSION_DAYS = 30
