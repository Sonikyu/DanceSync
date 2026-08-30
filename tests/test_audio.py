"""Format decode smoke tests: wav (soundfile path), mp3/m4a (ffmpeg audio),
mov (ffmpeg video container). Requires ffmpeg on PATH for everything but wav.
"""

from __future__ import annotations

import shutil
import subprocess

import numpy as np
import pytest
import soundfile as sf

from dancesync import audio
from dancesync.config import SR

HAVE_FFMPEG = shutil.which("ffmpeg") is not None

pytestmark = pytest.mark.skipif(not HAVE_FFMPEG, reason="ffmpeg not installed")


def _make_wav(path, duration_sec=2.0, sr=44100):
    t = np.arange(int(duration_sec * sr)) / sr
    y = (0.3 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
    sf.write(str(path), y, sr, subtype="PCM_16")
    return y, sr


@pytest.fixture
def wav_path(tmp_path):
    path = tmp_path / "tone.wav"
    _make_wav(path)
    return path


@pytest.fixture
def mp3_path(tmp_path, wav_path):
    path = tmp_path / "tone.mp3"
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-i", str(wav_path), str(path)],
        check=True,
    )
    return path


@pytest.fixture
def m4a_path(tmp_path, wav_path):
    path = tmp_path / "tone.m4a"
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-i", str(wav_path), "-c:a", "aac", str(path)],
        check=True,
    )
    return path


@pytest.fixture
def mov_path(tmp_path, wav_path):
    path = tmp_path / "tone.mov"
    subprocess.run(
        [
            "ffmpeg", "-v", "error", "-y",
            "-f", "lavfi", "-i", "color=c=black:s=64x64:r=10",
            "-i", str(wav_path),
            "-c:v", "libx264", "-c:a", "aac",
            "-shortest", str(path),
        ],
        check=True,
    )
    return path


def test_decode_wav(wav_path):
    y = audio.decode(wav_path, sr=SR, use_cache=False)
    assert y.dtype == np.float32
    assert y.ndim == 1
    assert audio.duration_sec(y, SR) == pytest.approx(2.0, abs=0.05)


def test_decode_mp3(mp3_path):
    y = audio.decode(mp3_path, sr=SR, use_cache=False)
    assert y.size > 0
    assert audio.duration_sec(y, SR) == pytest.approx(2.0, abs=0.2)


def test_decode_m4a(m4a_path):
    y = audio.decode(m4a_path, sr=SR, use_cache=False)
    assert y.size > 0
    assert audio.duration_sec(y, SR) == pytest.approx(2.0, abs=0.2)


def test_decode_mov_container(mov_path):
    y = audio.decode(mov_path, sr=SR, use_cache=False)
    assert y.size > 0
    assert audio.duration_sec(y, SR) == pytest.approx(2.0, abs=0.2)


def test_decode_caches_by_content(wav_path, monkeypatch, tmp_path):
    cache_dir = tmp_path / "cache"
    monkeypatch.setattr(audio, "CACHE_DIR", cache_dir)

    y1 = audio.decode(wav_path, sr=SR, use_cache=True)
    cached_files = list((cache_dir / "audio").glob("*.npy"))
    assert len(cached_files) == 1

    y2 = audio.decode(wav_path, sr=SR, use_cache=True)
    assert np.array_equal(y1, y2)
    # still exactly one cache entry -- the second decode was a cache hit
    assert len(list((cache_dir / "audio").glob("*.npy"))) == 1


def test_unsupported_extension_raises(tmp_path):
    path = tmp_path / "notes.txt"
    path.write_text("not audio")
    with pytest.raises(audio.DecodeError):
        audio.decode(path, sr=SR, use_cache=False)


def test_missing_file_raises(tmp_path):
    with pytest.raises(audio.DecodeError):
        audio.decode(tmp_path / "nope.wav", sr=SR, use_cache=False)
