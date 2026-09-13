"""Alignment and sync job runner. Synchronous for v1 -- a background queue is Phase 5.

A thin wrapper around the Phase 1 matcher and the Phase 3 sync engine. The
reference's content-hash id doubles as the cache key for its time-stretched
features, so aligning many clips against the same reference only pays the
stretch cost once.
"""

from __future__ import annotations

from pathlib import Path

from dancesync import audio, matcher, sync
from dancesync.sync import Sound
from dancesync.types import MatchResult
from server.models import Layout


def align_clip(clip_path: Path, reference_path: Path, reference_id: str) -> MatchResult:
    clip_audio = audio.decode(clip_path)
    ref_audio = audio.decode(reference_path)
    ref_features = matcher.precompute_ref_features(ref_audio, cache_key=reference_id)
    return matcher.match(clip_audio, ref_audio, ref_features=ref_features)


def sync_clip(
    clip_path: Path,
    reference_path: Path,
    rate: float,
    offset_sec: float,
    out_path: Path,
    sound: Sound,
    layout: Layout,
) -> None:
    """Render the synced video unless an earlier request already did. The
    caller names `out_path` after everything the render depends on, so an
    existing file is never stale."""
    if out_path.exists():
        return
    if layout == "side-by-side":
        sync.render_side_by_side(clip_path, reference_path, rate, offset_sec, out_path, sound)
    else:
        sync.render_synced(clip_path, reference_path, rate, offset_sec, out_path, sound)
