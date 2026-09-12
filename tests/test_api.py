"""Route tests: upload -> auto-align -> select, against synthetic audio."""

from __future__ import annotations

import pytest

from tests.conftest import make_clip, make_reference, upload_reference, wav_bytes


def test_upload_reference(client):
    ref_audio = make_reference(duration_sec=20.0, seed=1)
    reference = upload_reference(client, ref_audio)

    assert reference["filename"] == "song.wav"
    assert reference["duration_sec"] == pytest.approx(20.0, abs=0.05)

    listed = client.get("/api/references").json()
    assert [r["id"] for r in listed] == [reference["id"]]


def test_reference_reupload_is_idempotent(client):
    ref_audio = make_reference(duration_sec=20.0, seed=1)
    first = upload_reference(client, ref_audio)
    second = upload_reference(client, ref_audio)

    assert first["id"] == second["id"]
    assert len(client.get("/api/references").json()) == 1


def test_unsupported_reference_format_rejected(client):
    files = {"file": ("notes.txt", b"not audio", "text/plain")}
    resp = client.post("/api/references", files=files)
    assert resp.status_code == 415


def test_upload_clip_returns_alignment_candidates(client):
    ref_audio = make_reference(duration_sec=60.0, seed=2)
    reference = upload_reference(client, ref_audio)

    clip = make_clip(ref_audio, start_sec=10.0, duration_sec=15.0, rate=0.75, snr_db=10.0)
    files = {"file": ("practice.wav", wav_bytes(clip.audio), "audio/wav")}
    resp = client.post(
        "/api/clips", params={"reference_id": reference["id"]}, files=files
    )
    assert resp.status_code == 201, resp.text

    body = resp.json()
    assert body["reference_id"] == reference["id"]
    candidates = body["alignment"]["top_candidates"]
    assert 1 <= len(candidates) <= 3
    assert candidates[0]["rate"] == pytest.approx(0.75, abs=1e-6)
    assert candidates[0]["offset_sec"] == pytest.approx(10.0, abs=0.5)

    fetched = client.get(f"/api/clips/{body['id']}").json()
    assert fetched == body


def test_upload_clip_unknown_reference_404s(client):
    clip_audio = make_reference(duration_sec=5.0, seed=3)
    files = {"file": ("practice.wav", wav_bytes(clip_audio), "audio/wav")}
    resp = client.post("/api/clips", params={"reference_id": "nope"}, files=files)
    assert resp.status_code == 404


def test_select_candidate_persists(client):
    ref_audio = make_reference(duration_sec=60.0, seed=4)
    reference = upload_reference(client, ref_audio)

    clip = make_clip(ref_audio, start_sec=20.0, duration_sec=15.0, rate=1.0, snr_db=10.0)
    files = {"file": ("practice.wav", wav_bytes(clip.audio), "audio/wav")}
    upload_resp = client.post(
        "/api/clips", params={"reference_id": reference["id"]}, files=files
    )
    clip_id = upload_resp.json()["id"]

    select_resp = client.post(f"/api/clips/{clip_id}/select", json={"index": 0})
    assert select_resp.status_code == 200
    assert select_resp.json()["alignment"]["selected_index"] == 0

    fetched = client.get(f"/api/clips/{clip_id}").json()
    assert fetched["alignment"]["selected_index"] == 0


def test_select_candidate_out_of_range_rejected(client):
    ref_audio = make_reference(duration_sec=60.0, seed=5)
    reference = upload_reference(client, ref_audio)

    clip = make_clip(ref_audio, start_sec=5.0, duration_sec=15.0, rate=1.0, snr_db=10.0)
    files = {"file": ("practice.wav", wav_bytes(clip.audio), "audio/wav")}
    upload_resp = client.post(
        "/api/clips", params={"reference_id": reference["id"]}, files=files
    )
    clip_id = upload_resp.json()["id"]

    resp = client.post(f"/api/clips/{clip_id}/select", json={"index": 99})
    assert resp.status_code == 400
