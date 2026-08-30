from __future__ import annotations

import numpy as np
import pytest

from dancesync.config import HOP, SR
from dancesync.features import featurize, frames_to_sec, normalize, sec_to_frames


def test_frames_to_sec_known_values():
    assert frames_to_sec(0) == 0.0
    assert frames_to_sec(1) == pytest.approx(HOP / SR)
    assert frames_to_sec(100) == pytest.approx(100 * HOP / SR)


def test_sec_to_frames_round_trip():
    seconds = np.array([0.0, 1.0, 2.5, 10.0, 59.999])
    frames = sec_to_frames(seconds)
    back = frames_to_sec(frames)
    assert np.allclose(back, seconds, atol=(HOP / SR))


def test_frames_to_sec_array_input():
    frames = np.array([0, 10, 20])
    result = frames_to_sec(frames)
    assert np.allclose(result, frames * HOP / SR)


def test_normalize_zero_mean_unit_variance():
    rng = np.random.default_rng(0)
    feat = rng.normal(loc=5.0, scale=3.0, size=(12, 500))

    normed = normalize(feat)

    assert np.allclose(normed.mean(axis=1), 0.0, atol=1e-6)
    assert np.allclose(normed.std(axis=1), 1.0, atol=1e-6)


def test_normalize_handles_constant_row_without_nan():
    feat = np.ones((12, 100))
    normed = normalize(feat)
    assert np.all(np.isfinite(normed))


def test_featurize_shape():
    sr = SR
    y = np.sin(2 * np.pi * 440 * np.arange(sr * 2) / sr).astype(np.float32)
    feat = featurize(y, sr=sr, hop=HOP)
    assert feat.shape[0] == 12
    assert feat.shape[1] > 0
