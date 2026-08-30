"""Decode any container the phone or the music library might hand us.

Everything downstream sees the same thing: mono float32 at config.SR. Video
files are accepted only so their audio track can be pulled out -- no frame ever
reaches the matcher.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np

from spike.config import SR, CACHE_DIR

# iPhone's native camera writes .mov (HEVC/H.264 + AAC); Voice Memos writes
# .m4a; shared/compressed exports land as .mp4. The rest are here so that a
# reference library of mixed downloads just works.
VIDEO_EXTS = {".mov", ".mp4", ".m4v", ".avi", ".mkv", ".webm", ".3gp", ".mpg", ".mpeg"}
AUDIO_EXTS = {".wav", ".aif", ".aiff", ".flac", ".mp3", ".m4a", ".aac", ".ogg",
              ".oga", ".opus", ".caf", ".wma", ".alac", ".au", ".w64"}
SUPPORTED_EXTS = VIDEO_EXTS | AUDIO_EXTS

# libsndfile handles these directly and fast; everything else goes via ffmpeg.
_SOUNDFILE_EXTS = {".wav", ".aif", ".aiff", ".flac", ".ogg", ".oga", ".caf", ".au", ".w64"}


class DecodeError(RuntimeError):
    pass


@dataclass
class Probe:
    path: Path
    duration_sec: Optional[float]
    sample_rate: Optional[int]
    channels: Optional[int]
    codec: Optional[str]
    has_video: bool

    def summary(self) -> str:
        dur = f"{self.duration_sec:7.1f}s" if self.duration_sec else "      ?s"
        kind = "video+audio" if self.has_video else "audio"
        return f"{dur}  {self.codec or '?':<10} {self.sample_rate or '?':>6} Hz  {self.channels or '?'}ch  {kind}"


def have_ffmpeg() -> bool:
    return shutil.which("ffmpeg") is not None


def is_supported(path: Path) -> bool:
    return path.suffix.lower() in SUPPORTED_EXTS


def needs_ffmpeg(path: Path) -> bool:
    return path.suffix.lower() not in _SOUNDFILE_EXTS


# --- probing --------------------------------------------------------------

def probe(path: Path) -> Probe:
    """Best-effort metadata. Uses ffprobe when present, soundfile otherwise."""
    path = Path(path)
    if shutil.which("ffprobe"):
        try:
            return _probe_ffprobe(path)
        except Exception:
            pass
    try:
        import soundfile as sf

        info = sf.info(str(path))
        return Probe(path, info.duration, info.samplerate, info.channels,
                     info.subtype or info.format, has_video=False)
    except Exception:
        return Probe(path, None, None, None, None, has_video=False)


def _probe_ffprobe(path: Path) -> Probe:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_format", "-show_streams",
         "-print_format", "json", str(path)],
        capture_output=True, text=True, check=True,
    ).stdout
    meta = json.loads(out)
    streams = meta.get("streams", [])
    audio = next((s for s in streams if s.get("codec_type") == "audio"), None)
    has_video = any(s.get("codec_type") == "video" for s in streams)
    duration = meta.get("format", {}).get("duration")
    return Probe(
        path=path,
        duration_sec=float(duration) if duration else None,
        sample_rate=int(audio["sample_rate"]) if audio and audio.get("sample_rate") else None,
        channels=int(audio["channels"]) if audio and audio.get("channels") else None,
        codec=audio.get("codec_name") if audio else None,
        has_video=has_video,
    )


# --- decoding -------------------------------------------------------------

def load_audio(path: Path, sr: int = SR, use_cache: bool = True) -> np.ndarray:
    """Return mono float32 audio at `sr`.

    Decoded results are cached as .npy, keyed on path+mtime+size+sr. Re-running
    the matcher over a folder of .mov files is otherwise dominated by ffmpeg.
    """
    path = Path(path).resolve()
    if not path.exists():
        raise DecodeError(f"no such file: {path}")

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


def file_key(path: Path, **params) -> str:
    """Stable digest of a file's identity plus analysis parameters.

    Used to key both decoded audio and derived features, so editing or
    replacing a file silently invalidates everything computed from it.
    """
    path = Path(path).resolve()
    st = path.stat()
    extra = "|".join(f"{k}={params[k]}" for k in sorted(params))
    key = f"{path}|{st.st_mtime_ns}|{st.st_size}|{extra}"
    return hashlib.sha1(key.encode()).hexdigest()[:16]


def _cache_path(path: Path, sr: int) -> Path:
    return CACHE_DIR / f"{Path(path).stem}-{file_key(path, sr=sr)}.npy"


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
            f"{path.name} needs ffmpeg to decode (iPhone .mov/.m4a and .mp4 are "
            f"not readable by libsndfile).\n  Install it with:  brew install ffmpeg"
        )
    cmd = [
        "ffmpeg", "-v", "error", "-nostdin",
        "-i", str(path),
        "-vn",                 # drop video: audio only, per the spike's scope
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


def duration_sec(y: np.ndarray, sr: int = SR) -> float:
    return len(y) / float(sr)
