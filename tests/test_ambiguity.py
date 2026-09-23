"""`AMBIGUOUS_PEAK_RATIO` and `MIN_MATCH_SCORE` against material with a known
answer: a chorus that repeats word for word must be flagged ambiguous, a
passage heard once must not, and a take from another song must be flagged
failed while neither of those is. Guards both thresholds against future
matcher changes."""

from __future__ import annotations

import librosa
import numpy as np

from dancesync.config import AMBIGUOUS_PEAK_RATIO, MIN_MATCH_SCORE, SR
from dancesync.matcher import match
from tests.conftest import make_clip, make_reference


def _song_with_repeated_chorus() -> np.ndarray:
    """Verse 0-20 s, chorus 20-35 s, verse 35-55 s, the same chorus 55-70 s, outro 70-85 s."""
    chorus = make_reference(duration_sec=15.0, seed=2)
    parts = [
        make_reference(duration_sec=20.0, seed=1),
        chorus,
        make_reference(duration_sec=20.0, seed=3),
        chorus,
        make_reference(duration_sec=15.0, seed=4),
    ]
    return np.concatenate(parts)


def test_repeated_chorus_is_ambiguous():
    song = _song_with_repeated_chorus()
    clip = make_clip(song, start_sec=22.0, duration_sec=10.0, rate=0.75, snr_db=10.0)

    result = match(clip.audio, song)

    assert result.peak_ratio < AMBIGUOUS_PEAK_RATIO
    assert result.score >= MIN_MATCH_SCORE
    # Both choruses are offered, so the user can pick the one they danced.
    assert result.rank_of(22.0) is not None
    assert result.rank_of(57.0) is not None


def test_passage_heard_once_is_not_ambiguous(reference_audio):
    clip = make_clip(reference_audio, start_sec=100.0, duration_sec=20.0, rate=0.75, snr_db=10.0)

    result = match(clip.audio, reference_audio)

    assert result.peak_ratio >= AMBIGUOUS_PEAK_RATIO
    assert result.score >= MIN_MATCH_SCORE


def test_take_from_another_song_fails(reference_audio):
    """A different synthetic song, moved a tritone away so it shares no
    chords with the reference -- the synthetic stand-in for dancing to the
    wrong track. (Untransposed, two synthetic songs share the generator's
    eight chords and score 5-7 against each other; real songs don't.)"""
    other_song = librosa.effects.pitch_shift(make_reference(duration_sec=40.0, seed=3), sr=SR, n_steps=6)
    clip = make_clip(other_song, start_sec=5.0, duration_sec=20.0, rate=0.75, snr_db=10.0)

    result = match(clip.audio, reference_audio)

    assert result.score < MIN_MATCH_SCORE
