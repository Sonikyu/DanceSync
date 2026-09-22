"""Every tunable in one place.

Several of these values must agree across `features.py` and `matcher.py` to
stay correct (frame size, rate list, overlap floor). Change them here, not at
call sites.
"""

import os
from pathlib import Path

# --- Audio / feature parameters -------------------------------------------

SR = 22050          # analysis sample rate; chroma does not need more
HOP = 512           # 23.2 ms per feature frame at SR=22050
N_CHROMA = 12

# Playback rates to search. 1.0 = normal, 0.75 = the primary product case.
RATES = (1.0, 0.75, 0.5)

# A lag is only scored if the clip and reference overlap by at least this
# fraction of the clip. Dividing correlation by overlap length stops
# mid-reference bias, but without a floor it makes 1-frame overlaps at the
# edges look like perfect matches.
MIN_OVERLAP_FRAC = 0.5

# When measuring peak_ratio, ignore other peaks within this many seconds of
# the winner -- they are the same match, not a competing one.
PEAK_EXCLUDE_SEC = 2.0

# Below this peak_ratio the winner isn't clearly better than the next-best
# part of the song, so the UI asks the user to pick instead of committing.
# Measured: a chorus repeated word for word scores 1.04-1.06 (synthetic and
# the real Tier B song alike); passages heard once score 1.4-2.0, dipping to
# 1.15 at worst. Erring high costs the user one extra click; erring low
# renders the wrong part of the song.
AMBIGUOUS_PEAK_RATIO = 1.2

# --- Synced video output ----------------------------------------------------

# H.264 Constrained Baseline + AAC-LC plays in every browser <video> element.
# CRF 18 is visually lossless -- the dancer's phone footage is their source of
# truth. The preset trades file size for speed, not quality: on an M-series
# Mac, veryfast encoded 20 s of 1080p in 1.0 s, medium in 2.5 s for a file
# only a few percent smaller.
VIDEO_PROFILE = "baseline"
VIDEO_CRF = 18
VIDEO_PRESET = "veryfast"
AUDIO_BITRATE = "192k"

# Side-by-side renders scale both videos to one height and put them on one
# frame grid. 60 fps is above any phone clip re-timed from 30 fps (40 at
# 0.75x, 60 at 0.5x), so frames only ever get duplicated, never dropped.
SIDE_BY_SIDE_HEIGHT = 720
SIDE_BY_SIDE_FPS = 60

# --- Paths ------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent

# Cached decoded audio and time-stretched reference features. Keyed on content
# hash rather than mtime, since uploaded files may be re-uploaded with the
# same bytes but a fresh mtime.
CACHE_DIR = Path(os.environ.get("DANCESYNC_CACHE_DIR", ROOT / ".cache" / "dancesync"))


def ensure_cache_dir() -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
