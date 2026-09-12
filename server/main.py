"""FastAPI app: CORS, router registration, storage directory setup."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from server.config import ALLOWED_ORIGINS, STORAGE_ROOT
from server.routes import align, clips, references


@asynccontextmanager
async def lifespan(app: FastAPI):
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
