"""Manual alignment: PUT / DELETE /api/clips/{id}/manual, and every render
using the effective alignment (manual, else the chosen candidate)."""

from __future__ import annotations

import json

import pytest

from server.models import AlignmentResult
from server.routes import synced as synced_routes
from tests.conftest import make_clip, make_reference, upload_clip, upload_reference

REF_SEC = 60.0
# A 0.75x recording of 15 s of song lasts 20 s.
CLIP_SEC = 20.0


@pytest.fixture
def clip(client) -> dict:
    ref_audio = make_reference(duration_sec=REF_SEC, seed=24)
    reference = upload_reference(client, ref_audio)
    take = make_clip(ref_audio, start_sec=10.0, duration_sec=15.0, rate=0.75, snr_db=10.0)
    return upload_clip(client, reference["id"], take.audio)


def _put(client, clip_id, rate, offset_sec):
    return client.put(f"/api/clips/{clip_id}/manual", json={"rate": rate, "offset_sec": offset_sec})


def test_put_then_get_returns_the_manual_values(client, clip):
    resp = _put(client, clip["id"], 0.8, 10.15)

    assert resp.status_code == 200
    assert resp.json()["alignment"]["manual"] == {"rate": 0.8, "offset_sec": 10.15}
    assert client.get(f"/api/clips/{clip['id']}").json()["alignment"]["manual"] == {"rate": 0.8, "offset_sec": 10.15}


def test_delete_restores_the_matchers_result_exactly(client, clip):
    _put(client, clip["id"], 0.8, 10.15)

    resp = client.delete(f"/api/clips/{clip['id']}/manual")

    assert resp.status_code == 200
    assert resp.json() == clip
    assert client.get(f"/api/clips/{clip['id']}").json() == clip


@pytest.mark.parametrize("rate", [0.2, 1.05])
def test_out_of_range_rate_is_rejected(client, clip, rate):
    assert _put(client, clip["id"], rate, 10.0).status_code == 422


@pytest.mark.parametrize(
    ("offset_sec", "status"),
    [(-CLIP_SEC - 0.5, 422), (-CLIP_SEC + 0.5, 200), (REF_SEC - 0.5, 200), (REF_SEC + 0.5, 422)],
)
def test_offset_must_leave_some_of_the_take_over_the_song(client, clip, offset_sec, status):
    assert _put(client, clip["id"], 0.75, offset_sec).status_code == status


def test_unknown_clip_404s(client):
    assert _put(client, "nope", 0.75, 1.0).status_code == 404
    assert client.delete("/api/clips/nope/manual").status_code == 404


def test_picking_a_candidate_drops_the_manual_alignment(client, clip):
    _put(client, clip["id"], 0.8, 10.15)

    resp = client.post(f"/api/clips/{clip['id']}/select", json={"index": 1})

    assert resp.json()["alignment"]["manual"] is None
    assert resp.json()["alignment"]["selected_index"] == 1


def test_records_saved_before_manual_existed_still_load():
    saved = {"top_candidates": [{"rate": 0.75, "offset_sec": 1.0, "score": 9.0, "peak_ratio": None}], "ambiguous": False}

    alignment = AlignmentResult.model_validate_json(json.dumps(saved))

    assert alignment.manual is None


def test_render_uses_the_manual_values_and_a_new_file(client, clip, monkeypatch):
    renders = []

    def fake_sync_clip(clip_path, reference_path, params, out_path):
        if out_path.exists():
            return False
        renders.append((params.rate, params.offset_sec, out_path.name))
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(b"not really an mp4")
        return True

    monkeypatch.setattr(synced_routes, "sync_clip", fake_sync_clip)
    url = f"/api/clips/{clip['id']}/synced"
    automatic = clip["alignment"]["top_candidates"][0]

    client.get(url)
    _put(client, clip["id"], 0.8, 10.15)
    client.get(url)
    client.delete(f"/api/clips/{clip['id']}/manual")
    client.get(url)

    assert [(rate, offset) for rate, offset, _ in renders] == [
        (automatic["rate"], automatic["offset_sec"]), (0.8, 10.15),
    ]
    assert renders[0][2] != renders[1][2]   # the tuned render is its own file
    # Back to automatic serves the first render again: no third render.
