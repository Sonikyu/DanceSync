"""Every tunable in one place.

Several of these values must agree across `features.py` and `matcher.py` to
stay correct (frame size, rate list, overlap floor). Change them here, not at
call sites.
"""

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

# --- Paths ------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent

# Cached decoded audio and time-stretched reference features. Keyed on content
# hash rather than mtime, since uploaded files may be re-uploaded with the
# same bytes but a fresh mtime.
CACHE_DIR = ROOT / ".cache" / "dancesync"


def ensure_cache_dir() -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
