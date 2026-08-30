"""Chroma features and the normalization the spec calls out as load-bearing."""

from __future__ import annotations

import numpy as np

from spike.config import SR, HOP


def chroma(y: np.ndarray, sr: int = SR, hop: int = HOP) -> np.ndarray:
    """(12, n_frames) constant-Q chroma."""
    import librosa

    return librosa.feature.chroma_cqt(y=y, sr=sr, hop_length=hop)


def normalize(feat: np.ndarray) -> np.ndarray:
    """Z-score each feature dimension over time.

    Without this, a loud room and a quiet room produce features with different
    means, and the correlation is dominated by that offset rather than by
    harmonic content. Centering also makes a mismatch score near zero instead
    of merely "smaller", which is what lets peak_ratio mean anything.
    """
    mean = feat.mean(axis=1, keepdims=True)
    std = feat.std(axis=1, keepdims=True)
    std = np.maximum(std, 1e-8)
    return (feat - mean) / std


def featurize(y: np.ndarray, sr: int = SR, hop: int = HOP) -> np.ndarray:
    return normalize(chroma(y, sr=sr, hop=hop))


def frames_to_sec(frames, sr: int = SR, hop: int = HOP):
    """Feature-frame index -> seconds. Deliberately one function, used everywhere.

    The spec flags frame/second conversion as a prime source of Tier A bugs;
    keeping a single conversion means an error here shows up as a constant
    offset in every result rather than as a subtle inconsistency.
    """
    return np.asarray(frames) * hop / float(sr)


def sec_to_frames(seconds, sr: int = SR, hop: int = HOP):
    return np.round(np.asarray(seconds) * float(sr) / hop).astype(int)
