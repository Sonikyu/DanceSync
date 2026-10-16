"""Edits: PUT /api/references/{id}/framing and PUT /api/clips/{id}/edits,
their validation, and every render naming the edits it applied."""

from __future__ import annotations

import json

import pytest

from server.models import Clip, Reference
from server.routes import clips as clip_routes
from server.routes import synced as synced_routes
from tests.conftest import make_clip, make_reference, upload_clip, upload_reference

# A 0.75x recording of 15 s of song lasts 20 s.
CLIP_SEC = 20.0
FRAMING = {"rotate": 90, "crop": {"x": 0.1, "y": 0.2, "w": 0.5, "h": 0.6}, "mirror": True}
UNEDITED = {"rotate": 0, "crop": None, "mirror": False}


@pytest.fixture
def clip(client) -> dict:
    ref_audio = make_reference(duration_sec=60.0, seed=31)
    reference = upload_reference(client, ref_audio)
    take = make_clip(ref_audio, start_sec=10.0, duration_sec=15.0, rate=0.75, snr_db=10.0)
    return upload_clip(client, reference["id"], take.audio)


def _put_edits(client, clip_id, framing=UNEDITED, trim=None):
    return client.put(f"/api/clips/{clip_id}/edits", json={"framing": framing, "trim": trim})


def test_new_records_are_unedited(clip):
    assert clip["framing"] == UNEDITED
    assert clip["trim"] is None


def test_reference_framing_round_trips(client, clip):
    resp = client.put(f"/api/references/{clip['reference_id']}/framing", json=FRAMING)

    assert resp.status_code == 200
    assert resp.json()["framing"] == FRAMING
    assert client.get("/api/references").json()[0]["framing"] == FRAMING


def test_clip_edits_round_trip(client, clip):
    trim = {"start_sec": 1.5, "end_sec": 18.0}
    resp = _put_edits(client, clip["id"], FRAMING, trim)

    assert resp.status_code == 200
    saved = client.get(f"/api/clips/{clip['id']}").json()
    assert (saved["framing"], saved["trim"]) == (FRAMING, trim)
    assert saved["alignment"] == clip["alignment"]


def test_clearing_edits_restores_the_unedited_clip(client, clip):
    _put_edits(client, clip["id"], FRAMING, {"start_sec": 1.5, "end_sec": 18.0})

    assert _put_edits(client, clip["id"]).json() == clip


@pytest.mark.parametrize(
    "crop",
    [
        {"x": -0.1, "y": 0.0, "w": 0.5, "h": 0.5},   # off the left edge
        {"x": 0.6, "y": 0.0, "w": 0.5, "h": 0.5},    # off the right edge
        {"x": 0.0, "y": 0.7, "w": 0.5, "h": 0.5},    # off the bottom
        {"x": 0.0, "y": 0.0, "w": 0.1, "h": 0.5},    # narrower than MIN_CROP_FRAC
        {"x": 0.0, "y": 0.0, "w": 0.5, "h": 0.15},   # shorter than MIN_CROP_FRAC
    ],
)
def test_bad_crops_are_rejected(client, clip, crop):
    framing = {**UNEDITED, "crop": crop}

    assert _put_edits(client, clip["id"], framing).status_code == 422
    assert client.put(f"/api/references/{clip['reference_id']}/framing", json=framing).status_code == 422


def test_rotation_must_be_a_quarter_turn(client, clip):
    assert _put_edits(client, clip["id"], {**UNEDITED, "rotate": 45}).status_code == 422


@pytest.mark.parametrize(
    ("start_sec", "end_sec", "status"),
    [
        (0.0, CLIP_SEC, 200),
        (2.0, 10.0, 200),
        (-0.5, 10.0, 422),            # before the take starts
        (10.0, 10.0, 422),            # empty
        (12.0, 10.0, 422),            # backwards
        (2.0, CLIP_SEC + 1.0, 422),   # past the end
    ],
)
def test_trim_must_lie_inside_the_take(client, clip, start_sec, end_sec, status):
    trim = {"start_sec": start_sec, "end_sec": end_sec}

    assert _put_edits(client, clip["id"], trim=trim).status_code == status


def test_unknown_records_404(client):
    assert client.put("/api/references/nope/framing", json=UNEDITED).status_code == 404
    assert _put_edits(client, "nope").status_code == 404


def test_edits_never_re_align(client, clip, monkeypatch):
    def no_align(*args):
        raise AssertionError("an edit re-aligned the clip")

    monkeypatch.setattr(clip_routes, "align_clip", no_align)
    _put_edits(client, clip["id"], FRAMING, {"start_sec": 1.0, "end_sec": 5.0})
    client.put(f"/api/references/{clip['reference_id']}/framing", json=FRAMING)

    assert client.get(f"/api/clips/{clip['id']}").json()["alignment"] == clip["alignment"]


def test_records_saved_before_edits_existed_still_load():
    reference = {"id": "r", "filename": "song.mp4", "duration_sec": 60.0, "created_at": "2025-01-01T00:00:00Z"}
    alignment = {"top_candidates": [{"rate": 0.75, "offset_sec": 1.0, "score": 9.0, "peak_ratio": None}], "ambiguous": False}
    clip = {"id": "c", "reference_id": "r", "filename": "take.mov", "alignment": alignment, "created_at": "2025-01-01T00:00:00Z"}

    assert Reference.model_validate_json(json.dumps(reference)).framing.crop is None
    loaded = Clip.model_validate_json(json.dumps(clip))
    assert (loaded.framing.rotate, loaded.trim) == (0, None)


def test_every_edit_renders_to_a_new_file(client, clip, monkeypatch):
    renders = []

    def fake_sync_clip(clip_path, reference_path, params, edits, out_path):
        if out_path.exists():
            return False
        renders.append((edits, out_path.name))
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(b"not really an mp4")
        return True

    monkeypatch.setattr(synced_routes, "sync_clip", fake_sync_clip)
    url = f"/api/clips/{clip['id']}/synced"

    client.get(url)
    client.put(f"/api/references/{clip['reference_id']}/framing", json=FRAMING)
    client.get(url)
    _put_edits(client, clip["id"], FRAMING)
    client.get(url)
    _put_edits(client, clip["id"], FRAMING, {"start_sec": 1.0, "end_sec": 5.0})
    client.get(url)
    client.get(url)   # unchanged: served from the cache

    names = [name for _, name in renders]
    assert len(names) == 4 and len(set(names)) == 4
    last_edits = renders[-1][0]
    assert last_edits.reference_framing.mirror and last_edits.take_framing.rotate == 90
    assert (last_edits.trim.start_sec, last_edits.trim.end_sec) == (1.0, 5.0)
