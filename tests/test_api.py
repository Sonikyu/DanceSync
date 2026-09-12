"""Route tests: upload -> auto-align -> select, against synthetic audio.

Each test gets its own storage root (a pytest tmp_path) via dependency
overrides, so tests never touch `.data/server` or each other's state.
"""

from __future__ import annotations

import io

import pytest
import soundfile as sf
from fastapi.testclient import TestClient

from dancesync.config import SR
from server.catalog import Catalog
from server.deps import get_catalog, get_storage
from server.main import app
from server.storage import LocalStorage
from tests.conftest import make_clip, make_reference


def _wav_bytes(y, sr: int = SR) -> bytes:
    buf = io.BytesIO()
    sf.write(buf, y, sr, format="WAV", subtype="FLOAT")
    return buf.getvalue()


@pytest.fixture
def client(tmp_path):
    app.dependency_overrides[get_storage] = lambda: LocalStorage(tmp_path / "media")
    app.dependency_overrides[get_catalog] = lambda: Catalog(tmp_path / "catalog")
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _upload_reference(client, ref_audio):
    files = {"file": ("song.wav", _wav_bytes(ref_audio), "audio/wav")}
    resp = client.post("/api/references", files=files)
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_upload_reference(client):
    ref_audio = make_reference(duration_sec=20.0, seed=1)
    reference = _upload_reference(client, ref_audio)

    assert reference["filename"] == "song.wav"
    assert reference["duration_sec"] == pytest.approx(20.0, abs=0.05)

    listed = client.get("/api/references").json()
    assert [r["id"] for r in listed] == [reference["id"]]


def test_reference_reupload_is_idempotent(client):
    ref_audio = make_reference(duration_sec=20.0, seed=1)
    first = _upload_reference(client, ref_audio)
    second = _upload_reference(client, ref_audio)

    assert first["id"] == second["id"]
    assert len(client.get("/api/references").json()) == 1


def test_unsupported_reference_format_rejected(client):
    files = {"file": ("notes.txt", b"not audio", "text/plain")}
    resp = client.post("/api/references", files=files)
    assert resp.status_code == 415


def test_upload_clip_returns_alignment_candidates(client):
    ref_audio = make_reference(duration_sec=60.0, seed=2)
    reference = _upload_reference(client, ref_audio)

    clip = make_clip(ref_audio, start_sec=10.0, duration_sec=15.0, rate=0.75, snr_db=10.0)
    files = {"file": ("practice.wav", _wav_bytes(clip.audio), "audio/wav")}
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
    files = {"file": ("practice.wav", _wav_bytes(clip_audio), "audio/wav")}
    resp = client.post("/api/clips", params={"reference_id": "nope"}, files=files)
    assert resp.status_code == 404


def test_select_candidate_persists(client):
    ref_audio = make_reference(duration_sec=60.0, seed=4)
    reference = _upload_reference(client, ref_audio)

    clip = make_clip(ref_audio, start_sec=20.0, duration_sec=15.0, rate=1.0, snr_db=10.0)
    files = {"file": ("practice.wav", _wav_bytes(clip.audio), "audio/wav")}
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
    reference = _upload_reference(client, ref_audio)

    clip = make_clip(ref_audio, start_sec=5.0, duration_sec=15.0, rate=1.0, snr_db=10.0)
    files = {"file": ("practice.wav", _wav_bytes(clip.audio), "audio/wav")}
    upload_resp = client.post(
        "/api/clips", params={"reference_id": reference["id"]}, files=files
    )
    clip_id = upload_resp.json()["id"]

    resp = client.post(f"/api/clips/{clip_id}/select", json={"index": 99})
    assert resp.status_code == 400
