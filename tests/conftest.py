"""Synthetic fixtures: a fake reference track and cut-and-stretch clips with
known ground truth. Ported from the spike's `synth.py` -- the same generator
that produced the spike's Tier A gate. Plus a flash video (a visual marker at
a known time, for checking where frames land after re-timing) and an API test
client with its own storage root.
"""

from __future__ import annotations

import io
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np
import pytest
import soundfile as sf
from fastapi.testclient import TestClient

from dancesync.config import SR
from server.catalog import Catalog
from server.deps import get_catalog, get_storage
from server.main import app
from server.storage import LocalStorage

# Deliberately non-repeating chord order. An earlier version of this generator
# cycled a fixed progression and produced a track that was exactly
# self-similar every 72s -- three tied correlation peaks, which looks like a
# matcher bug and is not one.
_CHORDS = [
    (261.63, 329.63, 392.00),   # C
    (392.00, 493.88, 587.33),   # G
    (440.00, 523.25, 659.26),   # Am
    (349.23, 440.00, 523.25),   # F
    (293.66, 349.23, 440.00),   # Dm
    (329.63, 392.00, 493.88),   # Em
    (246.94, 293.66, 369.99),   # Bdim-ish
    (220.00, 277.18, 329.63),   # A
]


@dataclass
class SyntheticClip:
    audio: np.ndarray
    true_offset_sec: float   # start position in the ORIGINAL reference timeline
    true_rate: float
    snr_db: Optional[float]


def make_reference(duration_sec: float = 180.0, sr: int = SR, seed: int = 7) -> np.ndarray:
    """A fake 'song': a non-repeating chord progression with a beat, standing
    in for real music so tests don't depend on a licensed audio fixture."""
    rng = np.random.default_rng(seed)
    chord_sec = 2.0
    n_chords = int(np.ceil(duration_sec / chord_sec))
    order = rng.integers(0, len(_CHORDS), size=n_chords)

    t_chord = np.arange(int(chord_sec * sr)) / sr
    envelope = np.exp(-1.5 * (t_chord % 0.5))

    blocks = []
    for i in range(n_chords):
        chord = _CHORDS[int(order[i])]
        block = np.zeros_like(t_chord)
        for f in chord:
            for harmonic, amp in ((1, 1.0), (2, 0.4), (3, 0.2)):
                block += amp * np.sin(2 * np.pi * f * harmonic * t_chord)
        block *= envelope / 3.0
        beat = np.zeros_like(t_chord)
        for b in range(int(chord_sec / 0.5)):
            start = int(b * 0.5 * sr)
            click = rng.normal(0, 1, size=int(0.02 * sr)) * np.exp(
                -np.linspace(0, 8, int(0.02 * sr))
            )
            beat[start:start + len(click)] += click
        blocks.append(block + 0.3 * beat)

    y = np.concatenate(blocks)[: int(duration_sec * sr)]
    return (y / (np.max(np.abs(y)) + 1e-9) * 0.7).astype(np.float32)


def add_white_noise(y: np.ndarray, snr_db: float, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    signal_power = float(np.mean(y.astype(np.float64) ** 2))
    if signal_power <= 0:
        return y
    noise_power = signal_power / (10.0 ** (snr_db / 10.0))
    noise = rng.normal(0.0, np.sqrt(noise_power), size=y.shape)
    return (y + noise).astype(np.float32)


def make_clip(
    ref_audio: np.ndarray,
    start_sec: float,
    duration_sec: float = 30.0,
    rate: float = 0.75,
    snr_db: Optional[float] = 10.0,
    sr: int = SR,
    seed: int = 0,
) -> SyntheticClip:
    """Cut, time-stretch, and add white noise. Ground truth is the cut
    position. `rate` follows librosa's convention: rate < 1 plays back
    slower, so a 0.75x clip is longer than the chunk it came from."""
    start = int(round(start_sec * sr))
    end = start + int(round(duration_sec * sr))
    if end > len(ref_audio):
        raise ValueError(
            f"chunk [{start_sec:.1f}s, {start_sec + duration_sec:.1f}s] runs past the "
            f"end of the reference ({len(ref_audio) / sr:.1f}s)"
        )

    chunk = np.ascontiguousarray(ref_audio[start:end], dtype=np.float32)

    if rate != 1.0:
        import librosa

        chunk = librosa.effects.time_stretch(chunk, rate=rate)

    if snr_db is not None:
        chunk = add_white_noise(chunk, snr_db=snr_db, seed=seed)

    return SyntheticClip(
        audio=np.ascontiguousarray(chunk, dtype=np.float32),
        true_offset_sec=start / float(sr),
        true_rate=rate,
        snr_db=snr_db,
    )


def write_flash_video(
    path: Path,
    duration_sec: float,
    flash_sec: float,
    audio_path: Optional[Path] = None,
    size: str = "64x64",
) -> None:
    """A black 30 fps video, `size` pixels, that turns white at `flash_sec`.
    With `audio_path`, that file becomes the soundtrack, like a phone filming
    a laptop speaker."""
    video_source = (
        f"color=c=black:s={size}:r=30:d={duration_sec},"
        f"drawbox=c=white:t=fill:enable='gte(t,{flash_sec})'"
    )
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", video_source]
    if audio_path is not None:
        cmd += ["-i", str(audio_path), "-c:a", "aac"]
    cmd += ["-c:v", "libx264", "-pix_fmt", "yuv420p", str(path)]
    subprocess.run(cmd, check=True)


def flash_time_sec(video_path: Path) -> float:
    """When the first white frame appears. Frames are resampled onto a fixed
    100 fps grid first, so this reads true timestamps whatever the file's
    own frame rate."""
    cmd = [
        "ffmpeg", "-v", "error", "-i", str(video_path),
        "-vf", "scale=1:1,format=gray,fps=100", "-f", "rawvideo", "-",
    ]
    luma = np.frombuffer(subprocess.run(cmd, capture_output=True, check=True).stdout, np.uint8)
    return int(np.argmax(luma > 128)) / 100


def wav_bytes(y: np.ndarray, sr: int = SR) -> bytes:
    """32-bit integer PCM, not float: libsndfile stamps the current time into
    a float WAV's PEAK chunk, so the same audio a second later gave different
    bytes -- and a different content-hash id on upload."""
    buf = io.BytesIO()
    sf.write(buf, y, sr, format="WAV", subtype="PCM_32")
    return buf.getvalue()


def upload_reference(client: TestClient, ref_audio: np.ndarray) -> dict:
    files = {"file": ("song.wav", wav_bytes(ref_audio), "audio/wav")}
    resp = client.post("/api/references", files=files)
    assert resp.status_code == 201, resp.text
    return resp.json()


def upload_clip(client: TestClient, reference_id: str, clip_audio: np.ndarray) -> dict:
    files = {"file": ("practice.wav", wav_bytes(clip_audio), "audio/wav")}
    resp = client.post("/api/clips", params={"reference_id": reference_id}, files=files)
    assert resp.status_code == 201, resp.text
    return resp.json()


@pytest.fixture(scope="session")
def reference_audio() -> np.ndarray:
    return make_reference(duration_sec=180.0, sr=SR, seed=7)


@pytest.fixture
def client(tmp_path):
    """Each test gets its own storage root via dependency overrides, so tests
    never touch `.data/server` or each other's state."""
    app.dependency_overrides[get_storage] = lambda: LocalStorage(tmp_path / "media")
    app.dependency_overrides[get_catalog] = lambda: Catalog(tmp_path / "catalog")
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
