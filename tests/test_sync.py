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
from dancesync.config import COMPARE_FPS, COMPARE_HEIGHT, COMPARE_WIDTH, SR
from dancesync.ffmpeg import SyncError
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
    with pytest.raises(SyncError, match="no video stream"):
        sync.render_synced(reference_path, reference_path, 1.0, 0.0, tmp_path / "out.mp4")


def test_failed_render_leaves_no_file(clip_path, tmp_path):
    out_dir = tmp_path / "out"
    with pytest.raises(SyncError):
        sync.render_synced(clip_path, tmp_path / "missing.wav", 1.0, 0.0, out_dir / "synced.mp4")
    assert list(out_dir.iterdir()) == []


def test_room_sound_is_the_phone_recording_sped_up(reference_path, tmp_path):
    """The phone heard a click at clip time 1.0 s; at 0.75x it lands at 0.75 s.
    The song's own click (reference 11.5 s) would land at 1.5 s instead."""
    room = tmp_path / "room.wav"
    _write_click_reference(room, duration_sec=CLIP_SEC, click_sec=1.0)
    clip = tmp_path / "practice.mp4"
    write_flash_video(clip, duration_sec=CLIP_SEC, flash_sec=FLASH_SEC, audio_path=room)
    out = tmp_path / "synced.mp4"
    sync.render_synced(clip, reference_path, rate=0.75, offset_sec=10.0, out_path=out, sound="room")

    _, duration = _probe(out)
    assert duration == pytest.approx(CLIP_SEC * 0.75, abs=0.05)
    assert _click_time_sec(out) == pytest.approx(0.75, abs=0.02)
    assert flash_time_sec(out) == pytest.approx(FLASH_SEC * 0.75, abs=FRAME_SEC + 0.01)


# ffmpeg crop windows (w:h:x:y) onto one part of a compare render. The top
# and bottom strips stay well inside the reference and the take for any
# stacked render in these tests.
_REGIONS = {
    "left": "iw/2:ih:0:0",
    "right": "iw/2:ih:iw/2:0",
    "top": "iw:ih/5:0:0",
    "bottom": "iw:ih/5:0:ih*4/5",
}


def _flash_time_in_sec(video_path, region: str) -> float:
    """Like `flash_time_sec`, but watching only one region of the frame."""
    cmd = [
        "ffmpeg", "-v", "error", "-i", str(video_path),
        "-vf", f"crop={_REGIONS[region]},scale=1:1,format=gray,fps=100", "-f", "rawvideo", "-",
    ]
    luma = np.frombuffer(subprocess.run(cmd, capture_output=True, check=True).stdout, np.uint8)
    return int(np.argmax(luma > 128)) / 100


def _write_flash_reference(tmp_path, duration_sec, flash_sec, size="64x64"):
    """A reference *video*: flashes white at `flash_sec`, with a click there too."""
    song = tmp_path / "song-audio.wav"
    _write_click_reference(song, duration_sec=duration_sec, click_sec=flash_sec)
    path = tmp_path / "choreography.mp4"
    write_flash_video(path, duration_sec=duration_sec, flash_sec=flash_sec, audio_path=song, size=size)
    return path


def test_side_by_side_lines_up_reference_and_take(clip_path, tmp_path):
    """The reference flashes at 11.5 s: the moment the practice session heard
    at clip time 2.0 s, when the clip flashes (rate 0.75, offset 10 s). Both
    halves flash together at 1.5 s -- reference left, take right."""
    reference = _write_flash_reference(tmp_path, duration_sec=20.0, flash_sec=11.5)
    out = tmp_path / "side.mp4"
    sync.render_compare(clip_path, reference, rate=0.75, offset_sec=10.0, out_path=out, layout="side-by-side")

    streams, duration = _probe(out)
    # Both test videos are square, so each half is as wide as it is tall.
    assert (streams["video"]["width"], streams["video"]["height"]) == (
        2 * COMPARE_HEIGHT, COMPARE_HEIGHT,
    )
    assert duration == pytest.approx(CLIP_SEC * 0.75, abs=0.05)
    assert np.allclose(np.diff(_frame_times_sec(out)), 1 / COMPARE_FPS, atol=1e-3)
    assert _flash_time_in_sec(out, "left") == pytest.approx(1.5, abs=FRAME_SEC + 0.01)
    assert _flash_time_in_sec(out, "right") == pytest.approx(1.5, abs=FRAME_SEC + 0.01)
    assert _click_time_sec(out) == pytest.approx(1.5, abs=0.01)


def test_side_by_side_holds_black_until_a_late_song_starts(clip_path, tmp_path):
    """Recording started 1 s before the song: the reference's flash at 1.0 s
    shows up 2.0 s into the output, after a second of black."""
    reference = _write_flash_reference(tmp_path, duration_sec=10.0, flash_sec=1.0)
    out = tmp_path / "side.mp4"
    sync.render_compare(clip_path, reference, rate=1.0, offset_sec=-1.0, out_path=out, layout="side-by-side")

    assert _flash_time_in_sec(out, "left") == pytest.approx(2.0, abs=FRAME_SEC + 0.01)


@pytest.mark.parametrize("layout", ["side-by-side", "stacked"])
def test_compare_with_audio_only_song_raises(clip_path, reference_path, tmp_path, layout):
    with pytest.raises(SyncError, match="no video stream"):
        sync.render_compare(clip_path, reference_path, 1.0, 0.0, tmp_path / "out.mp4", layout=layout)


def test_stacked_command_fits_width_and_stacks_vertically(clip_path, reference_path):
    cmd = sync.build_compare_command(clip_path, reference_path, 0.75, 10.0, CLIP_SEC, "stacked", "song")
    filtergraph = cmd[cmd.index("-filter_complex") + 1]

    assert f"scale={COMPARE_WIDTH}:-2" in filtergraph
    assert "vstack=inputs=2" in filtergraph
    assert "hstack" not in filtergraph


def test_stacked_puts_a_landscape_reference_over_the_take(clip_path, tmp_path):
    """A 16:9 reference over a square take, both 720 wide: 406 + 720 high
    (405 rounded to even). Same timing as side by side -- both flash at 1.5 s."""
    reference = _write_flash_reference(tmp_path, duration_sec=20.0, flash_sec=11.5, size="160x90")
    out = tmp_path / "stacked.mp4"
    sync.render_compare(clip_path, reference, rate=0.75, offset_sec=10.0, out_path=out, layout="stacked")

    streams, duration = _probe(out)
    assert (streams["video"]["width"], streams["video"]["height"]) == (COMPARE_WIDTH, 406 + COMPARE_WIDTH)
    assert streams["video"]["profile"] == "Constrained Baseline"
    assert duration == pytest.approx(CLIP_SEC * 0.75, abs=0.05)
    assert _flash_time_in_sec(out, "top") == pytest.approx(1.5, abs=FRAME_SEC + 0.01)
    assert _flash_time_in_sec(out, "bottom") == pytest.approx(1.5, abs=FRAME_SEC + 0.01)
    assert _click_time_sec(out) == pytest.approx(1.5, abs=0.01)
