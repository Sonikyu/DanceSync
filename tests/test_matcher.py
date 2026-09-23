"""Tier A regression suite: synthetic clips with exact ground truth.

Ported from the spike's `tier_a.py` gate. A failure here is a bug in the
matcher -- indexing, normalization, or frame/second conversion -- not a
finding about real-world audio. Usual suspects if this starts failing:

  - frame <-> second conversion (features.frames_to_sec)
  - the stretched-timeline -> original-timeline rescale in matcher.match
  - z-scoring the wrong axis in features.normalize
  - overlap normalization / masking in matcher.sliding_correlation
"""

from __future__ import annotations

import numpy as np
import pytest

from dancesync.config import MIN_MATCH_SCORE, SR
from dancesync.matcher import find_peaks, match, sliding_correlation
from tests.conftest import make_clip

TOLERANCE_SEC = 0.05   # ~50ms, per the spec
DURATION_SEC = 30.0

# Two positions well inside the 180s reference, so nothing runs off either end.
STARTS = [round(180.0 * f) for f in (0.30, 0.60)]
RATES = [1.0, 0.75]
SNRS = [None, 20.0, 10.0]


def _case_id(start, rate, snr):
    snr_label = "clean" if snr is None else f"{snr:g}dB"
    return f"t{start:g}s_r{rate:g}_{snr_label}"


CASES = [
    (start, rate, snr)
    for start in STARTS
    for rate in RATES
    for snr in SNRS
]


@pytest.mark.parametrize("start,rate,snr", CASES, ids=[_case_id(*c) for c in CASES])
def test_synthetic_recovery(reference_audio, start, rate, snr):
    clip = make_clip(
        reference_audio, start_sec=start, duration_sec=DURATION_SEC,
        rate=rate, snr_db=snr, sr=SR, seed=0,
    )

    result = match(clip.audio, reference_audio, rates=(1.0, 0.75, 0.5), sr=SR)

    assert result.rate == pytest.approx(clip.true_rate, abs=1e-9)
    assert result.offset_sec == pytest.approx(clip.true_offset_sec, abs=TOLERANCE_SEC)
    # A normal take is never reported as an outright failure.
    assert result.score >= MIN_MATCH_SCORE


def test_ambiguous_match_ranks_truth_in_top_candidates(reference_audio):
    """Even when the top-1 pick is imperfect, the true offset should surface
    somewhere in the top-N -- the signal behind the top-3 fallback UX."""
    clip = make_clip(
        reference_audio, start_sec=54.0, duration_sec=DURATION_SEC,
        rate=0.75, snr_db=10.0, sr=SR, seed=1,
    )

    result = match(clip.audio, reference_audio, rates=(1.0, 0.75, 0.5), sr=SR, top_k=3)

    assert result.rank_of(clip.true_offset_sec, tol_sec=0.5) is not None


def test_match_result_top_candidates_ordered_by_score(reference_audio):
    clip = make_clip(
        reference_audio, start_sec=90.0, duration_sec=DURATION_SEC,
        rate=0.75, snr_db=10.0, sr=SR, seed=0,
    )

    result = match(clip.audio, reference_audio, rates=(1.0, 0.75, 0.5), sr=SR, top_k=3)

    scores = [c.score for c in result.top_candidates]
    assert scores == sorted(scores, reverse=True)
    assert len(result.top_candidates) <= 3


def test_clip_longer_than_reference_raises():
    short_ref = np.zeros(SR * 5, dtype=np.float32)
    clip = np.zeros(SR * 10, dtype=np.float32)
    with pytest.raises(ValueError):
        match(clip, short_ref, rates=(1.0,), sr=SR)


def test_sliding_correlation_perfect_match_at_zero_lag():
    rng = np.random.default_rng(0)
    ref_f = rng.normal(size=(12, 200)).astype(np.float32)
    clip_f = ref_f[:, :50]

    lags, scores = sliding_correlation(clip_f, ref_f)
    best_lag = int(lags[np.argmax(scores)])

    assert best_lag == 0


def test_find_peaks_suppresses_neighbors():
    scores = np.array([0.0, 5.0, 4.9, 0.0, 3.0, 0.0])
    lags = np.arange(len(scores))

    peaks = find_peaks(lags, scores, k=2, exclude_frames=1)

    assert peaks[0] == (1, 5.0)
    # the neighbor at lag=2 is suppressed by the exclusion window
    assert peaks[1][0] != 2
