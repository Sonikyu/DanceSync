"""The matcher: overlap-normalized sliding chroma correlation across rates."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import numpy as np

from spike.config import (
    SR, HOP, RATES, MIN_OVERLAP_FRAC, PEAK_EXCLUDE_SEC, CACHE_DIR,
)
from spike.features import featurize, frames_to_sec


@dataclass
class Peak:
    rate: float
    offset_sec: float      # in the ORIGINAL reference timeline
    score: float


@dataclass
class RateScores:
    rate: float
    lags: np.ndarray       # clip start position, in stretched-reference frames
    scores: np.ndarray     # overlap-normalized correlation, -inf where masked
    offsets_sec: np.ndarray  # lags converted to original-reference seconds


@dataclass
class MatchResult:
    rate: float
    offset_sec: float
    score: float
    peak_ratio: float
    top_peaks: List[Peak] = field(default_factory=list)
    per_rate: List[RateScores] = field(default_factory=list)

    def rank_of(self, true_offset_sec: float, tol_sec: float = 0.5) -> Optional[int]:
        """1-based rank of the first top-peak matching the truth, else None.

        The spec asks whether the correct answer shows up in the top 3 even when
        the top 1 is wrong -- that is the signal behind the thumbnail-fallback UX.
        """
        for i, p in enumerate(self.top_peaks, start=1):
            if abs(p.offset_sec - true_offset_sec) <= tol_sec:
                return i
        return None


def sliding_correlation(
    clip_f: np.ndarray,
    ref_f: np.ndarray,
    min_overlap_frac: float = MIN_OVERLAP_FRAC,
) -> Tuple[np.ndarray, np.ndarray]:
    """Correlate (12, m) clip against (12, n) reference at every alignment.

    Returns (lags, scores). `lags[i]` is the reference frame the clip would
    start at; scores are summed across chroma bins and divided by the number of
    overlapping frames, so a position with 200 overlapping frames is not
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

    # correlate(ref, clip) per bin via FFT, summed. convolving ref with the
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
) -> List[Tuple[int, float]]:
    """Top-k peaks with non-maximum suppression, as (lag, score)."""
    work = scores.copy()
    out: List[Tuple[int, float]] = []
    for _ in range(k):
        if not np.isfinite(work).any():
            break
        idx = int(np.argmax(work))
        out.append((int(lags[idx]), float(work[idx])))
        lo = max(0, idx - exclude_frames)
        hi = min(len(work), idx + exclude_frames + 1)
        work[lo:hi] = -np.inf
    return out


def precompute_ref_features(
    ref_audio: np.ndarray,
    rates: Tuple[float, ...] = RATES,
    sr: int = SR,
    hop: int = HOP,
    cache_key: Optional[str] = None,
) -> dict:
    """Stretch + featurize the reference once per rate, for reuse across clips.

    Time-stretching a full song is by far the expensive part of `match` -- tens
    of seconds per rate. Running many clips against one reference (the Tier A
    sweep, or all six Tier B clips) should pay that cost once, and with
    `cache_key` set it is paid once per reference ever.
    """
    import librosa

    cache_path = CACHE_DIR / f"reffeat-{cache_key}.npz" if cache_key else None
    if cache_path is not None and cache_path.exists():
        with np.load(cache_path) as data:
            cached = {float(k): data[k] for k in data.files}
        if all(r in cached for r in rates):
            return cached

    out = {}
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
    rates: Tuple[float, ...] = RATES,
    sr: int = SR,
    hop: int = HOP,
    stretch: str = "ref",
    min_overlap_frac: float = MIN_OVERLAP_FRAC,
    top_k: int = 3,
    ref_features: Optional[dict] = None,
) -> MatchResult:
    """Find where and at what playback rate `clip_audio` sits inside `ref_audio`.

    `stretch` selects which side is resampled:

      "ref"  - stretch the reference to each candidate rate (what the spec
               specifies). Faithful, but time-stretches a full song per rate.
      "clip" - stretch the 30 s clip back up to reference speed instead. Much
               cheaper, and it moves the phase-vocoder artifacts onto the clip.
               Worth trying if 0.75x fails and you suspect stretch artifacts
               rather than the recording chain.

    The returned offset is always in the ORIGINAL reference timeline.
    """
    import librosa

    if stretch not in ("ref", "clip"):
        raise ValueError("stretch must be 'ref' or 'clip'")

    exclude_frames = max(1, int(round(PEAK_EXCLUDE_SEC * sr / hop)))

    per_rate: List[RateScores] = []
    all_peaks: List[Peak] = []

    ref_f_plain = featurize(ref_audio, sr=sr, hop=hop) if stretch == "clip" else None
    clip_f_plain = featurize(clip_audio, sr=sr, hop=hop) if stretch == "ref" else None

    for rate in rates:
        if stretch == "ref":
            if ref_features is not None and rate in ref_features:
                ref_f = ref_features[rate]
            else:
                ref_y = (ref_audio if rate == 1.0
                         else librosa.effects.time_stretch(ref_audio, rate=rate))
                ref_f = featurize(ref_y, sr=sr, hop=hop)
            clip_f = clip_f_plain
            # A point at original time t appears at t/rate in the stretched
            # reference, so stretched-timeline seconds map back by *rate.
            to_original = rate
        else:
            clip_y = clip_audio if rate == 1.0 else librosa.effects.time_stretch(
                clip_audio, rate=1.0 / rate
            )
            clip_f = featurize(clip_y, sr=sr, hop=hop)
            ref_f = ref_f_plain
            to_original = 1.0

        if clip_f.shape[1] > ref_f.shape[1]:
            # Clip longer than the reference at this rate: nothing to align.
            continue

        lags, scores = sliding_correlation(clip_f, ref_f, min_overlap_frac)
        offsets = frames_to_sec(lags, sr=sr, hop=hop) * to_original
        per_rate.append(RateScores(rate=rate, lags=lags, scores=scores, offsets_sec=offsets))

        for lag, score in find_peaks(lags, scores, k=top_k, exclude_frames=exclude_frames):
            all_peaks.append(
                Peak(rate=rate,
                     offset_sec=float(frames_to_sec(lag, sr=sr, hop=hop) * to_original),
                     score=score)
            )

    if not per_rate:
        raise ValueError("no rate produced a usable alignment (clip longer than reference?)")

    all_peaks.sort(key=lambda p: p.score, reverse=True)
    winner = all_peaks[0]

    # peak_ratio compares the winner against the best competing peak in the SAME
    # rate curve, excluding its immediate neighbourhood. A repeated chorus drags
    # this toward 1.0, which is exactly the ambiguity signal clip 6 tests for.
    win_curve = next(rs for rs in per_rate if rs.rate == winner.rate)
    win_idx = int(np.argmax(win_curve.scores))
    masked = win_curve.scores.copy()
    lo = max(0, win_idx - exclude_frames)
    hi = min(len(masked), win_idx + exclude_frames + 1)
    masked[lo:hi] = -np.inf
    runner_up = float(np.max(masked)) if np.isfinite(masked).any() else 0.0
    peak_ratio = float(winner.score / runner_up) if runner_up > 1e-9 else float("inf")

    return MatchResult(
        rate=winner.rate,
        offset_sec=winner.offset_sec,
        score=winner.score,
        peak_ratio=peak_ratio,
        top_peaks=all_peaks[:top_k],
        per_rate=per_rate,
    )
