"""FastAPI app: startup checks, CORS, router registration, storage directory
setup, and the built web app."""

from __future__ import annotations

import logging
import shutil
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from dancesync.ffmpeg import ffmpeg_version, require_ffmpeg
from server.config import ALLOWED_ORIGINS, STORAGE_ROOT, WEB_DIST
from server.routes import align, clips, references, synced
from server.web import mount_web_app


log = logging.getLogger("uvicorn.error")


def check_ffmpeg() -> None:
    """Stop the server at startup, not deep inside the first upload, when
    ffmpeg is missing. `require_ffmpeg` raises with the install hint."""
    require_ffmpeg()
    log.info("Using %s (%s)", shutil.which("ffmpeg"), ffmpeg_version())


@asynccontextmanager
async def lifespan(app: FastAPI):
    check_ffmpeg()
    STORAGE_ROOT.mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(title="DanceSync API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(references.router)
app.include_router(clips.router)
app.include_router(align.router)
app.include_router(synced.router)

# Last, so its catch-all route never shadows an API route.
mount_web_app(app, WEB_DIST)
