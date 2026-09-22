"""How the sync engine runs ffmpeg: the presence check, probing, the shared
encoder settings, and writing output atomically. `sync.py` decides what to
render; this module only knows how to run ffmpeg and ffprobe.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import uuid
from pathlib import Path

from dancesync.config import AUDIO_BITRATE, VIDEO_CRF, VIDEO_PRESET, VIDEO_PROFILE


class SyncError(RuntimeError):
    pass


def require_ffmpeg() -> None:
    if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
        raise SyncError(
            "rendering a synced video needs ffmpeg and ffprobe.\n"
            "  Install them with:  brew install ffmpeg"
        )


def ffmpeg_version() -> str:
    """The first line of `ffmpeg -version`, e.g. "ffmpeg version 7.1 ..."."""
    proc = subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
    return _first_line(proc.stdout)


def probe_video_duration(path: Path) -> float:
    """Seconds of video in `path`, before re-timing."""
    cmd = [
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=duration:format=duration", "-of", "json", str(path),
    ]
    proc = subprocess.run(cmd, capture_output=True)
    if proc.returncode != 0:
        raise SyncError(f"ffprobe failed on {path.name}: {_last_line(proc.stderr)}")

    info = json.loads(proc.stdout)
    if not info.get("streams"):
        raise SyncError(f"{path.name} has no video stream")
    # Matroska/WebM leave the stream duration unset; fall back to the container's.
    return float(info["streams"][0].get("duration", info["format"]["duration"]))


def encode_args() -> list[str]:
    """Output settings shared by every render; config explains the choices."""
    return [
        "-c:v", "libx264", "-preset", VIDEO_PRESET, "-crf", str(VIDEO_CRF),
        "-profile:v", VIDEO_PROFILE, "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", AUDIO_BITRATE,
        # Index before media, so a browser can start playing mid-download.
        "-movflags", "+faststart",
    ]


def run_to_file(cmd: list[str], out_path: Path, clip_name: str) -> None:
    """Run `cmd` with an output path appended. ffmpeg writes to a temp file
    that is renamed into place only on success, so a failed render never
    leaves a truncated file that looks finished."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = out_path.with_name(f".tmp-{uuid.uuid4().hex}{out_path.suffix}")
    proc = subprocess.run([*cmd, str(tmp_path)], capture_output=True)
    if proc.returncode != 0:
        tmp_path.unlink(missing_ok=True)
        raise SyncError(f"ffmpeg failed on {clip_name}: {_last_line(proc.stderr)}")
    tmp_path.replace(out_path)


def _first_line(stdout: bytes) -> str:
    lines = stdout.decode("utf-8", "replace").strip().splitlines()
    return lines[0] if lines else "unknown version"


def _last_line(stderr: bytes) -> str:
    lines = stderr.decode("utf-8", "replace").strip().splitlines()
    return lines[-1] if lines else "unknown error"
