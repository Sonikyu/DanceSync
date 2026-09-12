"""Re-time a practice video to original speed and lay the reference audio under it.

The clip was filmed while the reference played at `rate`, and the matcher
places its start at `offset_sec` in the ORIGINAL reference timeline. So clip
time t heard reference time `offset_sec + t * rate`. Scaling every video
timestamp by `rate` moves clip time t to output time `t * rate`; output time
T then shows the moment that heard reference time `offset_sec + T` -- exactly
what the reference audio, cut to start at `offset_sec`, plays at T.

The clip's own audio (a laptop speaker through a phone mic) is discarded.
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


def render_synced(
    clip_path: Path,
    reference_path: Path,
    rate: float,
    offset_sec: float,
    out_path: Path,
) -> None:
    """Write the synced .mp4 to `out_path`.

    ffmpeg writes to a temp file that is renamed into place only on success,
    so a failed render never leaves a truncated file that looks finished.
    """
    _require_ffmpeg()
    video_duration_sec = probe_video_duration(clip_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = out_path.with_name(f".tmp-{uuid.uuid4().hex}{out_path.suffix}")

    cmd = build_command(clip_path, reference_path, rate, offset_sec, video_duration_sec, tmp_path)
    proc = subprocess.run(cmd, capture_output=True)
    if proc.returncode != 0:
        tmp_path.unlink(missing_ok=True)
        raise SyncError(f"ffmpeg failed on {clip_path.name}: {_last_line(proc.stderr)}")
    tmp_path.replace(out_path)


def build_command(
    clip_path: Path,
    reference_path: Path,
    rate: float,
    offset_sec: float,
    video_duration_sec: float,
    out_path: Path,
) -> list[str]:
    """The single ffmpeg invocation behind `render_synced`.

    A negative `offset_sec` means the phone started recording before the song
    did, so the reference is delayed by that much behind leading silence.
    Past the end of the reference the audio is padded with silence, so the
    whole video is always kept.
    """
    out_duration_sec = video_duration_sec * rate
    ref_start_sec = max(offset_sec, 0.0)
    lead_silence_ms = round(max(-offset_sec, 0.0) * 1000)
    filtergraph = (
        f"[0:v]setpts=PTS*{rate}[v];"
        f"[1:a]atrim=start={ref_start_sec:.6f},asetpts=PTS-STARTPTS,"
        f"adelay={lead_silence_ms}:all=1,apad[a]"
    )
    return [
        "ffmpeg", "-v", "error", "-nostdin",
        "-i", str(clip_path),
        "-i", str(reference_path),
        "-filter_complex", filtergraph,
        "-map", "[v]", "-map", "[a]",
        "-t", f"{out_duration_sec:.6f}",
        # Keep every frame the phone captured, just closer together (a 30 fps
        # clip at 0.75x comes out at 40 fps). Resampling back to 30 fps would
        # drop every fourth frame -- a visible stutter in fast movement.
        "-fps_mode", "passthrough",
        # setpts leaves the stream's nominal frame rate at 30, and by default
        # the encoder snaps timestamps onto that 1/30 s grid -- duplicating
        # or skipping the faster ones. Keep the input's fine time base instead.
        "-enc_time_base:v", "filter",
        "-c:v", "libx264", "-preset", VIDEO_PRESET, "-crf", str(VIDEO_CRF),
        "-profile:v", VIDEO_PROFILE, "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", AUDIO_BITRATE,
        # Index before media, so a browser can start playing mid-download.
        "-movflags", "+faststart",
        str(out_path),
    ]


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


def _require_ffmpeg() -> None:
    if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
        raise SyncError(
            "rendering a synced video needs ffmpeg and ffprobe.\n"
            "  Install them with:  brew install ffmpeg"
        )


def _last_line(stderr: bytes) -> str:
    lines = stderr.decode("utf-8", "replace").strip().splitlines()
    return lines[-1] if lines else "unknown error"
