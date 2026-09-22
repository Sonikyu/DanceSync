"""Server startup: the ffmpeg presence check stops the app before it serves."""

from __future__ import annotations

import shutil

import pytest
from fastapi.testclient import TestClient

from dancesync.ffmpeg import SyncError
from server.main import app


def test_startup_fails_without_ffmpeg(monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda name: None)

    with pytest.raises(SyncError, match="brew install ffmpeg"):
        with TestClient(app):
            pass


def test_startup_logs_ffmpeg_version(caplog):
    with caplog.at_level("INFO", logger="uvicorn.error"):
        with TestClient(app):
            pass

    assert "ffmpeg version" in caplog.text
