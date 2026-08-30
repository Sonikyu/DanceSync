"""Shared constants and paths for the alignment spike."""

from pathlib import Path

# --- Audio / feature parameters -------------------------------------------

SR = 22050          # analysis sample rate; chroma does not need more
HOP = 512           # 23.2 ms per feature frame at SR=22050
N_CHROMA = 12

# Playback rates to search. 1.0 = normal, 0.75 = the case the spike exists to test.
RATES = (1.0, 0.75, 0.5)

# A lag is only scored if the clip and reference overlap by at least this
# fraction of the clip. Dividing correlation by overlap length (see matcher)
# stops mid-reference bias, but without a floor it makes 1-frame overlaps at
# the edges look like perfect matches.
MIN_OVERLAP_FRAC = 0.5

# When measuring peak_ratio, ignore other peaks within this many seconds of
# the winner -- they are the same match, not a competing one.
PEAK_EXCLUDE_SEC = 2.0

# --- Paths ----------------------------------------------------------------

ROOT = Path(__file__).resolve().parent

DATA = ROOT / "data"
REFERENCE_DIR = DATA / "reference"    # full-length originals
CLIPS_DIR = DATA / "clips"            # Tier B phone recordings
SYNTHETIC_DIR = DATA / "synthetic"    # Tier A generated clips (regenerable)
INBOX_DIR = DATA / "inbox"            # drop zone; `ingest scan` files these
CACHE_DIR = DATA / "cache"            # decoded audio, as .npy
MANIFEST = DATA / "manifest.json"

OUT = ROOT / "out"
PLOTS_DIR = OUT / "plots"
RESULTS_DIR = OUT / "results"

ALL_DIRS = (
    REFERENCE_DIR, CLIPS_DIR, SYNTHETIC_DIR, INBOX_DIR, CACHE_DIR,
    PLOTS_DIR, RESULTS_DIR,
)


def ensure_dirs() -> None:
    for d in ALL_DIRS:
        d.mkdir(parents=True, exist_ok=True)
