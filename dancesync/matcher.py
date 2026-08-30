"""Overlap-normalized sliding chroma correlation across playback rates.

The reference is time-stretched to each candidate rate, so a peak found in the
stretched timeline is multiplied by `rate` to get back to the original. Every
offset returned by `match` is in the ORIGINAL reference timeline -- the one a
user would read off a normal audio editor. Breaking that invariant is the most
likely way to produce a plausible-looking wrong answer.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np

from dancesync.config import CACHE_DIR, HOP, MIN_OVERLAP_FRAC, PEAK_EXCLUDE_SEC, RATES, SR
from dancesync.features import featurize, frames_to_sec
from dancesync.types import Candidate, MatchResult


@dataclass
class RateScores:
    rate: float
    lags: np.ndarray          # clip start position, in stretched-reference frames
    scores: np.ndarray        # overlap-normalized correlation, -inf where masked
    offsets_sec: np.ndarray   # lags converted to original-reference seconds


def sliding_correlation(
    clip_f: np.ndarray,
    ref_f: np.ndarray,
    min_overlap_frac: float = MIN_OVERLAP_FRAC,
) -> tuple[np.ndarray, np.ndarray]:
    """Correlate (12, m) clip against (12, n) reference at every alignment.

    Returns (lags, scores). `lags[i]` is the reference frame the clip would
    start at; scores are summed across chroma bins and divided by the number
    of overlapping frames, so a position with 200 overlapping frames is not
    rewarded over one with 100 purely for having more terms to add up.
    """
    if clip_f.shape[0] != ref_f.shape[0]:
        raise ValueError("clip and reference must have the same number of feature bins")

    n_bins, m = clip_f.shape
    n = ref_f.shape[1]
    if m == 0 or n == 0:
        raise ValueError("empty feature matrix")

    full_len = n + m - 1
    nfft = 1 << int(np.ceil(np.log2(full_len)))

    # correlate(ref, clip) per bin via FFT, summed. Convolving ref with the
    # time-reversed clip gives the cross-correlation.
    ref_fft = np.fft.rfft(ref_f, n=nfft, axis=1)
    clip_fft = np.fft.rfft(clip_f[:, ::-1], n=nfft, axis=1)
    corr = np.fft.irfft(ref_fft * clip_fft, n=nfft, axis=1)[:, :full_len]
    scores = corr.sum(axis=0)

    lags = np.arange(full_len) - (m - 1)

    # Overlap length at each lag, then normalize.
    starts = np.maximum(lags, 0)
    ends = np.minimum(lags + m, n)
    overlap = np.maximum(ends - starts, 0)
    scores = scores / np.maximum(overlap, 1)

    # Mask the shallow-overlap tails: after dividing by overlap, a couple of
    # coincidentally-aligned frames at the edge can outscore a true match.
    min_overlap = max(1, int(round(min_overlap_frac * m)))
    scores = np.where(overlap >= min_overlap, scores, -np.inf)

    if not np.isfinite(scores).any():
        raise ValueError(
            "no lag has sufficient overlap -- is the clip longer than the reference?"
        )
    return lags, scores


def find_peaks(
    lags: np.ndarray,
    scores: np.ndarray,
    k: int = 3,
    exclude_frames: int = 1,
) -> list[tuple[int, float]]:
    """Top-k peaks with non-maximum suppression, as (lag, score)."""
    work = scores.copy()
    out: list[tuple[int, float]] = []
    for _ in range(k):
        if not np.isfinite(work).any():
            break
        idx = int(np.argmax(work))
        out.append((int(lags[idx]), float(work[idx])))
        lo = max(0, idx - exclude_frames)
        hi = min(len(work), idx + exclude_frames + 1)
        work[lo:hi] = -np.inf
    return out


def _peak_ratio_at(scores: np.ndarray, idx: int, exclude_frames: int) -> float:
    """Winner's score over the best competing peak outside its exclusion
    window. Self-similar music (repeated choruses) drags this toward 1.0 --
    that is the ambiguity signal for the top-N fallback UX."""
    masked = scores.copy()
    lo = max(0, idx - exclude_frames)
    hi = min(len(masked), idx + exclude_frames + 1)
    masked[lo:hi] = -np.inf
    if not np.isfinite(masked).any():
        return float("inf")
    runner_up = float(np.max(masked))
    winner = float(scores[idx])
    return winner / runner_up if runner_up > 1e-9 else float("inf")


def precompute_ref_features(
    ref_audio: np.ndarray,
    rates: tuple[float, ...] = RATES,
    sr: int = SR,
    hop: int = HOP,
    cache_key: Optional[str] = None,
) -> dict[float, np.ndarray]:
    """Stretch + featurize the reference once per rate, for reuse across clips.

    Time-stretching a full song is by far the expensive part of `match` --
    tens of seconds per rate. With `cache_key` set (e.g. the reference's
    content hash), the cost is paid once per reference ever, regardless of
    how many clips are matched against it.
    """
    import librosa

    cache_path = CACHE_DIR / "reffeat" / f"{cache_key}.npz" if cache_key else None
    if cache_path is not None and cache_path.exists():
        with np.load(cache_path) as data:
            cached = {float(k): data[k] for k in data.files}
        if all(r in cached for r in rates):
            return cached

    out: dict[float, np.ndarray] = {}
    for rate in rates:
        y = ref_audio if rate == 1.0 else librosa.effects.time_stretch(ref_audio, rate=rate)
        out[rate] = featurize(y, sr=sr, hop=hop)

    if cache_path is not None:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(cache_path, **{repr(float(r)): f for r, f in out.items()})
    return out


def match(
    clip_audio: np.ndarray,
    ref_audio: np.ndarray,
    rates: tuple[float, ...] = RATES,
    sr: int = SR,
    hop: int = HOP,
    min_overlap_frac: float = MIN_OVERLAP_FRAC,
    top_k: int = 3,
    ref_features: Optional[dict[float, np.ndarray]] = None,
) -> MatchResult:
    """Find where and at what playback rate `clip_audio` sits inside `ref_audio`.

    The reference is time-stretched to each candidate rate and correlated
    against the clip. Returns a `MatchResult` with up to `top_k` candidates,
    best first, each with an offset in the ORIGINAL reference timeline.
    """
    import librosa

    exclude_frames = max(1, int(round(PEAK_EXCLUDE_SEC * sr / hop)))
    clip_f = featurize(clip_audio, sr=sr, hop=hop)

    per_rate: list[RateScores] = []
    candidates: list[Candidate] = []

    for rate in rates:
        if ref_features is not None and rate in ref_features:
            ref_f = ref_features[rate]
        else:
            ref_y = ref_audio if rate == 1.0 else librosa.effects.time_stretch(ref_audio, rate=rate)
            ref_f = featurize(ref_y, sr=sr, hop=hop)

        if clip_f.shape[1] > ref_f.shape[1]:
            # Clip longer than the reference at this rate: nothing to align.
            continue

        lags, scores = sliding_correlation(clip_f, ref_f, min_overlap_frac)
        # A point at original time t appears at t/rate in the stretched
        # reference, so stretched-timeline seconds map back to the original
        # timeline by multiplying by rate.
        offsets = frames_to_sec(lags, sr=sr, hop=hop) * rate
        per_rate.append(RateScores(rate=rate, lags=lags, scores=scores, offsets_sec=offsets))

        for lag, score in find_peaks(lags, scores, k=top_k, exclude_frames=exclude_frames):
            idx = int(np.searchsorted(lags, lag))
            peak_ratio = _peak_ratio_at(scores, idx, exclude_frames)
            candidates.append(
                Candidate(
                    rate=rate,
                    offset_sec=float(frames_to_sec(lag, sr=sr, hop=hop) * rate),
                    score=score,
                    peak_ratio=peak_ratio,
                )
            )

    if not per_rate:
        raise ValueError("no rate produced a usable alignment (clip longer than reference?)")

    candidates.sort(key=lambda c: c.score, reverse=True)
    return MatchResult(top_candidates=tuple(candidates[:top_k]))
