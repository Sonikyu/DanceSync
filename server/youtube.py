"""YouTube import: check the link, probe its metadata, download the video.

yt-dlp runs as a subprocess, the way ffmpeg does, invoked through this
Python's `-m yt_dlp` so the venv's copy is always the one used. YouTube
breaks yt-dlp every few weeks; `pip install -U 'yt-dlp[default]'` is the fix.

Only the video id survives validation. yt-dlp is handed a URL rebuilt from
that id, never the one the user pasted, so it can't be pointed at another
site or an internal address.
"""

from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from server.config import MAX_IMPORT_BYTES, MAX_IMPORT_DURATION_SEC

WATCH_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com"}
SHORT_HOST = "youtu.be"
VIDEO_ID = re.compile(r"[A-Za-z0-9_-]{11}")

# Up to 1080p H.264 + AAC, merged into an MP4 every browser plays. Not capped
# lower: zooming in on one dancer needs the pixels.
FORMAT = "bv*[height<=1080][vcodec^=avc1]+ba[acodec^=mp4a]/b[height<=1080][ext=mp4]"


class YouTubeError(RuntimeError):
    """An import that can't go ahead. `status` is the HTTP status to answer."""

    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status


@dataclass
class VideoInfo:
    title: str
    duration_sec: float


def parse_video_id(url: str) -> str:
    """The 11-character id from a watch, shorts, m.youtube.com or youtu.be
    link. Checks the parsed host, not a substring of the URL."""
    parsed = urlparse(url.strip())
    host = (parsed.hostname or "").lower()
    if parsed.scheme not in ("http", "https"):
        raise YouTubeError(400, "not a YouTube link")
    if host == SHORT_HOST:
        candidate = parsed.path.lstrip("/")
    elif host in WATCH_HOSTS and parsed.path == "/watch":
        candidate = parse_qs(parsed.query).get("v", [""])[0]
    elif host in WATCH_HOSTS and parsed.path.startswith("/shorts/"):
        candidate = parsed.path.removeprefix("/shorts/").rstrip("/")
    else:
        raise YouTubeError(400, "not a YouTube link")
    if not VIDEO_ID.fullmatch(candidate):
        raise YouTubeError(400, "not a link to a YouTube video")
    return candidate


def watch_url(video_id: str) -> str:
    return f"https://www.youtube.com/watch?v={video_id}"


def is_installed() -> bool:
    return importlib.util.find_spec("yt_dlp") is not None


def probe(video_id: str) -> VideoInfo:
    """Metadata only, nothing downloaded. Rejects what can't or shouldn't be
    imported before a single video byte is fetched."""
    proc = _run_yt_dlp(["-J", watch_url(video_id)])
    if proc.returncode != 0:
        raise _probe_failure(proc.stderr)
    info = json.loads(proc.stdout)
    _check_importable(info)
    return VideoInfo(title=info.get("title") or video_id, duration_sec=float(info["duration"]))


def download(video_id: str, dest_dir: Path) -> Path:
    """Download into `dest_dir` and return the MP4's path."""
    out_template = str(dest_dir / "video.%(ext)s")
    args = ["-f", FORMAT, "--merge-output-format", "mp4",
            "--max-filesize", str(MAX_IMPORT_BYTES), "-o", out_template, watch_url(video_id)]
    proc = _run_yt_dlp(args)
    if proc.returncode != 0:
        raise YouTubeError(422, f"yt-dlp failed: {_last_line(proc.stderr)}")
    video_path = dest_dir / "video.mp4"
    # Over --max-filesize, yt-dlp skips the download and still exits 0.
    if not video_path.exists() or video_path.stat().st_size > MAX_IMPORT_BYTES:
        raise YouTubeError(413, f"video is over the {MAX_IMPORT_BYTES} byte import limit")
    return video_path


def safe_filename(title: str, video_id: str) -> str:
    """The title as a filename the song list can show: no path separators or
    control characters, and never empty."""
    cleaned = re.sub(r"[^\w\s().,'&!-]", "", title)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .")[:100]
    return f"{cleaned or video_id}.mp4"


def _check_importable(info: dict) -> None:
    if info.get("is_live") or info.get("live_status") in ("is_live", "is_upcoming", "post_live"):
        raise YouTubeError(422, "live streams can't be imported")
    if (info.get("age_limit") or 0) >= 18:
        raise YouTubeError(422, "age-restricted videos can't be imported")
    if info.get("availability") in ("private", "premium_only", "subscriber_only", "needs_auth"):
        raise YouTubeError(422, "private videos can't be imported")
    if not info.get("duration"):
        raise YouTubeError(422, "the video's length is unknown")
    if info["duration"] > MAX_IMPORT_DURATION_SEC:
        raise YouTubeError(413, f"video is over the {MAX_IMPORT_DURATION_SEC} s import limit")


def _probe_failure(stderr: bytes) -> YouTubeError:
    message = _last_line(stderr)
    lowered = message.lower()
    if "private video" in lowered:
        return YouTubeError(422, "private videos can't be imported")
    if "confirm your age" in lowered or "age-restricted" in lowered:
        return YouTubeError(422, "age-restricted videos can't be imported")
    return YouTubeError(422, f"yt-dlp failed: {message}")


def _run_yt_dlp(args: list[str]) -> subprocess.CompletedProcess:
    cmd = [sys.executable, "-m", "yt_dlp", "--no-playlist", "--no-progress", *args]
    return subprocess.run(cmd, capture_output=True)


def _last_line(stderr: bytes) -> str:
    lines = stderr.decode("utf-8", "replace").strip().splitlines()
    return lines[-1] if lines else "no error output"
