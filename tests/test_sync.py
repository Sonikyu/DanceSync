"""Sync engine tests. Timing is measured with markers at known times: a clip
that flashes white, and a reference that is silent except for one click.
Requires ffmpeg on PATH.
"""

from __future__ import annotations

import json
import shutil
import subprocess

import numpy as np
import pytest
import soundfile as sf

from dancesync import audio, sync
from dancesync.config import SR
from tests.conftest import flash_time_sec, write_flash_video

pytestmark = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")

CLIP_SEC = 4.0
FLASH_SEC = 2.0
FRAME_SEC = 1 / 30


def _write_click_reference(path, duration_sec, click_sec):
    """Silence with one 10 ms tone burst starting at `click_sec`."""
    y = np.zeros(int(duration_sec * SR), dtype=np.float32)
    t = np.arange(int(0.01 * SR)) / SR
    start = int(click_sec * SR)
    y[start:start + len(t)] = 0.8 * np.sin(2 * np.pi * 1000 * t)
    sf.write(str(path), y, SR)


def _click_time_sec(video_path) -> float:
    y = audio.decode(video_path, use_cache=False)
    return int(np.argmax(np.abs(y) > 0.4)) / SR


def _probe(path) -> tuple[dict, float]:
    """(streams keyed by codec_type, container duration in seconds)."""
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries",
        "stream=codec_type,codec_name,profile,pix_fmt,width,height"
        ":stream_side_data=rotation:format=duration",
        "-of", "json", str(path),
    ]
    info = json.loads(subprocess.run(cmd, capture_output=True, check=True).stdout)
    streams = {s["codec_type"]: s for s in info["streams"]}
    return streams, float(info["format"]["duration"])


def _frame_times_sec(path) -> np.ndarray:
    cmd = [
        "ffprobe", "-v", "error", "-select_streams", "v",
        "-show_entries", "frame=pts_time", "-of", "csv=p=0", str(path),
    ]
    lines = subprocess.run(cmd, capture_output=True, check=True, text=True).stdout.split()
    return np.array([float(line.split(",")[0]) for line in lines])


@pytest.fixture
def clip_path(tmp_path):
    path = tmp_path / "practice.mp4"
    write_flash_video(path, duration_sec=CLIP_SEC, flash_sec=FLASH_SEC)
    return path


@pytest.fixture
def reference_path(tmp_path):
    # At rate 0.75 and offset 10 s, the practice session heard reference time
    # 11.5 s at clip time (11.5 - 10) / 0.75 = 2.0 s -- the moment of the flash.
    path = tmp_path / "song.wav"
    _write_click_reference(path, duration_sec=20.0, click_sec=11.5)
    return path


def test_output_is_browser_playable(clip_path, reference_path, tmp_path):
    out = tmp_path / "synced.mp4"
    sync.render_synced(clip_path, reference_path, rate=0.75, offset_sec=10.0, out_path=out)

    streams, _ = _probe(out)
    assert streams["video"]["codec_name"] == "h264"
    assert streams["video"]["profile"] == "Constrained Baseline"
    assert streams["video"]["pix_fmt"] == "yuv420p"
    assert streams["audio"]["codec_name"] == "aac"
    assert streams["audio"]["profile"] == "LC"
    data = out.read_bytes()
    assert data.find(b"moov") < data.find(b"mdat")   # faststart


@pytest.mark.parametrize("rate", [1.0, 0.75, 0.5])
def test_video_sped_up_by_one_over_rate(clip_path, reference_path, tmp_path, rate):
    out = tmp_path / "synced.mp4"
    sync.render_synced(clip_path, reference_path, rate=rate, offset_sec=10.0, out_path=out)

    _, duration = _probe(out)
    frame_times = _frame_times_sec(out)
    assert duration == pytest.approx(CLIP_SEC * rate, abs=0.05)
    # Every frame kept, evenly spaced at the sped-up interval -- not snapped
    # onto the clip's original 1/30 s grid.
    assert len(frame_times) == CLIP_SEC * 30
    assert np.allclose(np.diff(frame_times), FRAME_SEC * rate, atol=1e-3)
    assert flash_time_sec(out) == pytest.approx(FLASH_SEC * rate, abs=FRAME_SEC + 0.01)


def test_video_and_reference_audio_line_up(clip_path, reference_path, tmp_path):
    """The flash and the click happened together in the practice session
    (see `reference_path`), so they must land together in the output."""
    out = tmp_path / "synced.mp4"
    sync.render_synced(clip_path, reference_path, rate=0.75, offset_sec=10.0, out_path=out)

    assert _click_time_sec(out) == pytest.approx(1.5, abs=0.01)
    assert flash_time_sec(out) == pytest.approx(1.5, abs=FRAME_SEC + 0.01)


def test_negative_offset_delays_reference(clip_path, tmp_path):
    """Recording started 1 s before the song: the reference's first second
    lands 1 s into the output."""
    reference = tmp_path / "song.wav"
    _write_click_reference(reference, duration_sec=20.0, click_sec=1.0)
    out = tmp_path / "synced.mp4"
    sync.render_synced(clip_path, reference, rate=1.0, offset_sec=-1.0, out_path=out)

    assert _click_time_sec(out) == pytest.approx(2.0, abs=0.01)


def test_reference_ending_early_keeps_whole_video(clip_path, tmp_path):
    reference = tmp_path / "short.wav"
    _write_click_reference(reference, duration_sec=5.0, click_sec=1.0)
    out = tmp_path / "synced.mp4"
    sync.render_synced(clip_path, reference, rate=1.0, offset_sec=3.0, out_path=out)

    _, duration = _probe(out)
    assert duration == pytest.approx(CLIP_SEC, abs=0.05)


def test_phone_rotation_baked_in(reference_path, tmp_path):
    """Phones store portrait video as landscape pixels plus a rotation flag.
    The output must have portrait pixels and no flag, or players rotate twice."""
    landscape = tmp_path / "landscape.mp4"
    subprocess.run(
        ["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=c=black:s=64x32:r=30:d=1",
         "-c:v", "libx264", "-pix_fmt", "yuv420p", str(landscape)],
        check=True,
    )
    portrait = tmp_path / "portrait.mov"
    subprocess.run(
        ["ffmpeg", "-v", "error", "-display_rotation:v:0", "90", "-i", str(landscape),
         "-c", "copy", str(portrait)],
        check=True,
    )
    out = tmp_path / "synced.mp4"
    sync.render_synced(portrait, reference_path, rate=1.0, offset_sec=0.0, out_path=out)

    streams, _ = _probe(out)
    assert (streams["video"]["width"], streams["video"]["height"]) == (32, 64)
    assert "side_data_list" not in streams["video"]


def test_audio_only_clip_raises(reference_path, tmp_path):
    with pytest.raises(sync.SyncError, match="no video stream"):
        sync.render_synced(reference_path, reference_path, 1.0, 0.0, tmp_path / "out.mp4")


def test_failed_render_leaves_no_file(clip_path, tmp_path):
    out_dir = tmp_path / "out"
    with pytest.raises(sync.SyncError):
        sync.render_synced(clip_path, tmp_path / "missing.wav", 1.0, 0.0, out_dir / "synced.mp4")
    assert list(out_dir.iterdir()) == []
