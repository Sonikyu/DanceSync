"""Re-time a practice video to original speed and lay the reference audio under it.

The clip was filmed while the reference played at `rate`, and the matcher
places its start at `offset_sec` in the ORIGINAL reference timeline. So clip
time t heard reference time `offset_sec + t * rate`. Scaling every video
timestamp by `rate` moves clip time t to output time `t * rate`; output time
T then shows the moment that heard reference time `offset_sec + T` -- exactly
what the reference audio, cut to start at `offset_sec`, plays at T.

Two variants share that timing. `sound="room"` keeps the phone's own recording
(a laptop speaker through a phone mic) instead of the reference audio, sped up
by 1/rate like the video. `render_compare` puts the reference video, cut to
the same stretch of the song, to the left of the take or above it.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from dancesync.config import COMPARE_FPS, COMPARE_HEIGHT, COMPARE_WIDTH
from dancesync.ffmpeg import encode_args, probe_video_duration, require_ffmpeg, run_to_file

# What plays under the video: the reference track, or the phone's own recording.
Sound = Literal["song", "room"]

# How the reference and the take share the frame: reference left or on top.
CompareLayout = Literal["side-by-side", "stacked"]

# Each layout scales both videos to one shared dimension, then joins them
# along the other. `-2` keeps the free dimension even, which yuv420p needs.
_COMPARE_FIT = {"side-by-side": f"scale=-2:{COMPARE_HEIGHT}", "stacked": f"scale={COMPARE_WIDTH}:-2"}
_COMPARE_STACK = {"side-by-side": "hstack", "stacked": "vstack"}


def render_synced(
    clip_path: Path,
    reference_path: Path,
    rate: float,
    offset_sec: float,
    out_path: Path,
    sound: Sound = "song",
) -> None:
    """Write the synced .mp4 to `out_path`."""
    require_ffmpeg()
    video_duration_sec = probe_video_duration(clip_path)
    cmd = build_command(clip_path, reference_path, rate, offset_sec, video_duration_sec, sound)
    run_to_file(cmd, out_path, clip_path.name)


def render_compare(
    clip_path: Path,
    reference_path: Path,
    rate: float,
    offset_sec: float,
    out_path: Path,
    layout: CompareLayout,
    sound: Sound = "song",
) -> None:
    """Write an .mp4 with the reference video and the synced take together:
    reference left and take right at one height, or reference on top at one width."""
    require_ffmpeg()
    video_duration_sec = probe_video_duration(clip_path)
    probe_video_duration(reference_path)   # raises if the song file has no picture
    cmd = build_compare_command(
        clip_path, reference_path, rate, offset_sec, video_duration_sec, layout, sound
    )
    run_to_file(cmd, out_path, clip_path.name)


def build_command(
    clip_path: Path,
    reference_path: Path,
    rate: float,
    offset_sec: float,
    video_duration_sec: float,
    sound: Sound,
) -> list[str]:
    """The ffmpeg invocation behind `render_synced`, minus the output path.

    A negative `offset_sec` means the phone started recording before the song
    did, so the reference is delayed by that much behind leading silence.
    Past the end of the reference the audio is padded with silence, so the
    whole video is always kept.
    """
    filtergraph = f"[0:v]setpts=PTS*{rate}[v];{_sound_filter(sound, rate, offset_sec)}"
    return [
        "ffmpeg", "-v", "error", "-nostdin",
        "-i", str(clip_path),
        "-i", str(reference_path),
        "-filter_complex", filtergraph,
        "-map", "[v]", "-map", "[a]",
        "-t", f"{video_duration_sec * rate:.6f}",
        # Keep every frame the phone captured, just closer together (a 30 fps
        # clip at 0.75x comes out at 40 fps). Resampling back to 30 fps would
        # drop every fourth frame -- a visible stutter in fast movement.
        "-fps_mode", "passthrough",
        # setpts leaves the stream's nominal frame rate at 30, and by default
        # the encoder snaps timestamps onto that 1/30 s grid -- duplicating
        # or skipping the faster ones. Keep the input's fine time base instead.
        "-enc_time_base:v", "filter",
        *encode_args(),
    ]


def build_compare_command(
    clip_path: Path,
    reference_path: Path,
    rate: float,
    offset_sec: float,
    video_duration_sec: float,
    layout: CompareLayout,
    sound: Sound,
) -> list[str]:
    """The ffmpeg invocation behind `render_compare`, minus the output path.

    The reference video is cut exactly like the reference audio: from
    `offset_sec`, behind black frames when that's negative. Each side is put
    on the same frame grid before stacking -- a re-timed take runs at 40 fps
    and a reference often at 24, and stacking them as-is interleaves both
    into an irregular, duplicate-timestamped stream.
    """
    ref_start_sec, lead_sec = _reference_cut(offset_sec)
    fit = f"{_COMPARE_FIT[layout]},fps={COMPARE_FPS}"
    filtergraph = (
        f"[1:v]trim=start={ref_start_sec:.6f},setpts=PTS-STARTPTS,"
        f"tpad=start_duration={lead_sec:.6f}:color=black,{fit}[ref];"
        f"[0:v]setpts=PTS*{rate},{fit}[take];"
        f"[ref][take]{_COMPARE_STACK[layout]}=inputs=2[v];"
        f"{_sound_filter(sound, rate, offset_sec)}"
    )
    return [
        "ffmpeg", "-v", "error", "-nostdin",
        "-i", str(clip_path),
        "-i", str(reference_path),
        "-filter_complex", filtergraph,
        "-map", "[v]", "-map", "[a]",
        "-t", f"{video_duration_sec * rate:.6f}",
        *encode_args(),
    ]


def _sound_filter(sound: Sound, rate: float, offset_sec: float) -> str:
    """The filtergraph chain that produces the output's [a] stream."""
    if sound == "room":
        # Sped up by 1/rate to match the video; atempo keeps the pitch.
        return f"[0:a]atempo={1 / rate:.6f},apad[a]"
    ref_start_sec, lead_sec = _reference_cut(offset_sec)
    return (
        f"[1:a]atrim=start={ref_start_sec:.6f},asetpts=PTS-STARTPTS,"
        f"adelay={round(lead_sec * 1000)}:all=1,apad[a]"
    )


def _reference_cut(offset_sec: float) -> tuple[float, float]:
    """(where the reference is cut from, how long the output waits before it
    starts) -- the wait is nonzero only when the phone started recording first."""
    return max(offset_sec, 0.0), max(-offset_sec, 0.0)
