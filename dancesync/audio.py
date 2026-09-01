"""Decode any supported audio or video container to mono float32 at `config.SR`.

This is the only module that knows about file formats. Everything downstream
sees mono float32 audio at a single sample rate. Video containers are accepted
only so their audio track can be pulled out via ffmpeg -- no frame is ever
decoded.
"""

from __future__ import annotations

import hashlib
import shutil
import subprocess
from pathlib import Path

import numpy as np

from dancesync.config import CACHE_DIR, SR

# iPhone's native camera writes .mov (HEVC/H.264 + AAC); Voice Memos writes
# .m4a; shared/compressed exports land as .mp4.
VIDEO_EXTS = {".mov", ".mp4", ".m4v", ".avi", ".mkv", ".webm", ".3gp", ".mpg", ".mpeg"}
AUDIO_EXTS = {".wav", ".aif", ".aiff", ".flac", ".mp3", ".m4a", ".aac", ".ogg",
              ".oga", ".opus", ".caf", ".wma", ".alac", ".au", ".w64"}
SUPPORTED_EXTS = VIDEO_EXTS | AUDIO_EXTS

# libsndfile handles these directly and fast; everything else goes via ffmpeg.
_SOUNDFILE_EXTS = {".wav", ".aif", ".aiff", ".flac", ".ogg", ".oga", ".caf", ".au", ".w64"}

_HASH_CHUNK = 1024 * 1024


class DecodeError(RuntimeError):
    pass


def have_ffmpeg() -> bool:
    return shutil.which("ffmpeg") is not None


def is_supported(path: Path) -> bool:
    return Path(path).suffix.lower() in SUPPORTED_EXTS


def needs_ffmpeg(path: Path) -> bool:
    return Path(path).suffix.lower() not in _SOUNDFILE_EXTS


def content_hash(path: Path) -> str:
    """Stream a sha256 of the file's bytes, so re-uploads with identical
    content reuse the cache even if the path or mtime changed."""
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(_HASH_CHUNK), b""):
            digest.update(chunk)
    return digest.hexdigest()[:32]


def decode(path: Path, sr: int = SR, use_cache: bool = True) -> np.ndarray:
    """Return mono float32 audio at `sr`, decoded from any supported container.

    Decoded results are cached as .npy, keyed on the file's content hash and
    `sr` -- not mtime, since an uploaded file may be replaced with byte-identical
    content under a fresh timestamp.
    """
    path = Path(path)
    if not path.exists():
        raise DecodeError(f"no such file: {path}")
    if not is_supported(path):
        raise DecodeError(f"unsupported format: {path.suffix} ({path.name})")

    cache_path = _cache_path(path, sr) if use_cache else None
    if cache_path is not None and cache_path.exists():
        return np.load(cache_path)

    if needs_ffmpeg(path):
        y = _decode_ffmpeg(path, sr)
    else:
        y = _decode_soundfile(path, sr)

    if y.size == 0:
        raise DecodeError(f"decoded 0 samples from {path.name} -- is there an audio track?")

    if cache_path is not None:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        np.save(cache_path, y)
    return y


def duration_sec(y: np.ndarray, sr: int = SR) -> float:
    return len(y) / float(sr)


def _cache_path(path: Path, sr: int) -> Path:
    return CACHE_DIR / "audio" / f"{content_hash(path)}-{sr}.npy"


def _decode_soundfile(path: Path, sr: int) -> np.ndarray:
    import soundfile as sf

    y, file_sr = sf.read(str(path), dtype="float32", always_2d=True)
    y = y.mean(axis=1)
    if file_sr != sr:
        import librosa

        y = librosa.resample(y, orig_sr=file_sr, target_sr=sr)
    return np.ascontiguousarray(y, dtype=np.float32)


def _decode_ffmpeg(path: Path, sr: int) -> np.ndarray:
    if not have_ffmpeg():
        raise DecodeError(
            f"{path.name} needs ffmpeg to decode (video containers and .m4a/.mp3 are "
            f"not readable by libsndfile).\n  Install it with:  brew install ffmpeg"
        )
    cmd = [
        "ffmpeg", "-v", "error", "-nostdin",
        "-i", str(path),
        "-vn",                 # drop video: audio only
        "-map", "a:0?",        # first audio stream if there is one
        "-ac", "1",            # mono
        "-ar", str(sr),
        "-f", "f32le", "-",
    ]
    proc = subprocess.run(cmd, capture_output=True)
    if proc.returncode != 0:
        err = proc.stderr.decode("utf-8", "replace").strip().splitlines()
        raise DecodeError(f"ffmpeg failed on {path.name}: {err[-1] if err else 'unknown error'}")
    return np.frombuffer(proc.stdout, dtype=np.float32).copy()
