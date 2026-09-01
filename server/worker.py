"""Alignment job runner. Synchronous for v1 -- a background queue is Phase 5.

A thin wrapper around the Phase 1 matcher: decode both files and align. The
reference's content-hash id doubles as the cache key for its time-stretched
features, so aligning many clips against the same reference only pays the
stretch cost once.
"""

from __future__ import annotations

from pathlib import Path

from dancesync import audio, matcher
from dancesync.types import MatchResult


def align_clip(clip_path: Path, reference_path: Path, reference_id: str) -> MatchResult:
    clip_audio = audio.decode(clip_path)
    ref_audio = audio.decode(reference_path)
    ref_features = matcher.precompute_ref_features(ref_audio, cache_key=reference_id)
    return matcher.match(clip_audio, ref_audio, ref_features=ref_features)
