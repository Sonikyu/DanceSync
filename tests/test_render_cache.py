"""The render cache stays under its cap, least recently used first, and never
loses a render that's being written or served."""

from __future__ import annotations

import os

from server import config, render_cache
from server.routes import synced as synced_routes
from tests.conftest import make_clip, make_reference, upload_clip, upload_reference


def _render(render_dir, name, size_bytes, age_sec):
    """A fake finished render, last used `age_sec` ago."""
    render_dir.mkdir(parents=True, exist_ok=True)
    path = render_dir / name
    path.write_bytes(b"x" * size_bytes)
    used_at = 1_700_000_000 - age_sec
    os.utime(path, (used_at, used_at))
    return path


def test_sweep_deletes_oldest_until_under_cap(tmp_path):
    oldest = _render(tmp_path, "a.mp4", 100, age_sec=30)
    middle = _render(tmp_path, "b.mp4", 100, age_sec=20)
    newest = _render(tmp_path, "c.mp4", 100, age_sec=10)

    deleted = render_cache.sweep(tmp_path, max_bytes=150, keep=newest)

    assert deleted == [oldest, middle]
    assert newest.exists()


def test_sweep_under_cap_deletes_nothing(tmp_path):
    render = _render(tmp_path, "a.mp4", 100, age_sec=10)

    assert render_cache.sweep(tmp_path, max_bytes=100, keep=render) == []


def test_sweep_never_deletes_the_render_being_served(tmp_path):
    served = _render(tmp_path, "old-but-requested.mp4", 100, age_sec=60)
    other = _render(tmp_path, "b.mp4", 100, age_sec=10)

    assert render_cache.sweep(tmp_path, max_bytes=100, keep=served) == [other]
    assert served.exists()


def test_sweep_never_deletes_a_render_in_progress(tmp_path):
    writing = _render(tmp_path, ".tmp-0123abcd.mp4", 1000, age_sec=60)
    finished = _render(tmp_path, "a.mp4", 100, age_sec=10)

    assert render_cache.sweep(tmp_path, max_bytes=0, keep=finished) == []
    assert writing.exists()


def test_touch_makes_a_render_recent(tmp_path):
    served_again = _render(tmp_path, "a.mp4", 100, age_sec=30)
    other = _render(tmp_path, "b.mp4", 100, age_sec=20)
    newest = _render(tmp_path, "c.mp4", 100, age_sec=10)

    render_cache.touch(served_again)

    assert render_cache.sweep(tmp_path, max_bytes=200, keep=newest) == [other]


def test_rendering_past_the_cap_evicts_and_rerenders(client, monkeypatch, tmp_path):
    """Two renders fit under the cap; a third evicts the least recently used,
    which then renders again, transparently, on its next request."""
    ref_audio = make_reference(duration_sec=60.0, seed=21)
    reference = upload_reference(client, ref_audio)
    clip = make_clip(ref_audio, start_sec=20.0, duration_sec=15.0, rate=1.0, snr_db=10.0)
    clip_id = upload_clip(client, reference["id"], clip.audio)["id"]
    renders = []

    def fake_sync_clip(clip_path, reference_path, rate, offset_sec, out_path, sound, layout):
        if out_path.exists():
            return False
        renders.append((sound, layout))
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(b"x" * 1000)
        return True

    monkeypatch.setattr(synced_routes, "sync_clip", fake_sync_clip)
    monkeypatch.setattr(config, "RENDER_CACHE_MAX_BYTES", 2000)
    url = f"/api/clips/{clip_id}/synced"

    assert client.get(url, params={"sound": "song"}).status_code == 200
    assert client.get(url, params={"sound": "room"}).status_code == 200
    _age_all_renders(tmp_path / "media" / "synced")
    assert client.get(url, params={"sound": "song"}).status_code == 200   # cached, now most recent
    assert client.get(url, params={"layout": "side-by-side"}).status_code == 200   # evicts room
    assert client.get(url, params={"sound": "room"}).status_code == 200   # rendered again

    assert renders == [("song", "take"), ("room", "take"), ("song", "side-by-side"), ("room", "take")]


def _age_all_renders(render_dir):
    """Push every render's mtime into the past, so the next touch is
    unambiguously newer even on a coarse-mtime filesystem."""
    for path in render_dir.iterdir():
        os.utime(path, (1_700_000_000, 1_700_000_000))
