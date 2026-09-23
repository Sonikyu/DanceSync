"""Route tests: upload -> auto-align -> select, against synthetic audio."""

from __future__ import annotations

import pytest

from dancesync.config import AMBIGUOUS_PEAK_RATIO, MIN_CLIP_SEC, MIN_MATCH_SCORE, SR
from dancesync.types import Candidate as MatchCandidate
from dancesync.types import MatchResult
from server.routes import clips as clip_routes
from tests.conftest import make_clip, make_reference, upload_clip, upload_reference, wav_bytes


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


def test_references_listed_newest_first(client):
    first = upload_reference(client, make_reference(duration_sec=10.0, seed=12))
    second = upload_reference(client, make_reference(duration_sec=10.0, seed=13))

    listed = client.get("/api/references").json()
    assert [r["id"] for r in listed] == [second["id"], first["id"]]


def test_reference_media_served_with_range_support(client):
    ref_audio = make_reference(duration_sec=20.0, seed=11)
    reference = upload_reference(client, ref_audio)
    url = f"/api/references/{reference['id']}/media"

    full = client.get(url)
    assert full.status_code == 200
    assert full.content == wav_bytes(ref_audio)

    # Byte ranges let the browser seek to a candidate's offset without
    # downloading the whole song first.
    partial = client.get(url, headers={"Range": "bytes=100-199"})
    assert partial.status_code == 206
    assert partial.content == full.content[100:200]


def test_reference_media_unknown_404s(client):
    assert client.get("/api/references/nope/media").status_code == 404


def _fake_match(*peak_ratios: float) -> MatchResult:
    candidates = tuple(
        MatchCandidate(rate=0.75, offset_sec=10.0 * i, score=1.0 - 0.1 * i, peak_ratio=ratio)
        for i, ratio in enumerate(peak_ratios)
    )
    return MatchResult(top_candidates=candidates)


@pytest.mark.parametrize(
    ("peak_ratio", "ambiguous"),
    [(AMBIGUOUS_PEAK_RATIO - 0.01, True), (AMBIGUOUS_PEAK_RATIO + 0.01, False)],
)
def test_ambiguous_flag_follows_winner_peak_ratio(client, monkeypatch, peak_ratio, ambiguous):
    monkeypatch.setattr(clip_routes, "align_clip", lambda *args: _fake_match(peak_ratio, 0.9))
    reference = upload_reference(client, make_reference(duration_sec=20.0, seed=14))

    body = upload_clip(client, reference["id"], make_reference(duration_sec=5.0, seed=15))
    assert body["alignment"]["ambiguous"] is ambiguous


def test_unrivaled_peak_round_trips_as_null(client, monkeypatch):
    """A winner with no competing peak has an infinite peak_ratio, which JSON
    can't carry. It comes back as null, and the clip still loads from the catalog."""
    monkeypatch.setattr(clip_routes, "align_clip", lambda *args: _fake_match(float("inf")))
    reference = upload_reference(client, make_reference(duration_sec=20.0, seed=16))

    body = upload_clip(client, reference["id"], make_reference(duration_sec=5.0, seed=17))
    assert body["alignment"]["top_candidates"][0]["peak_ratio"] is None
    assert body["alignment"]["ambiguous"] is False

    fetched = client.get(f"/api/clips/{body['id']}")
    assert fetched.status_code == 200
    assert fetched.json() == body


def test_clip_shorter_than_minimum_is_rejected(client):
    ref_audio = make_reference(duration_sec=60.0, seed=18)
    reference = upload_reference(client, ref_audio)
    clip = make_clip(ref_audio, start_sec=10.0, duration_sec=5.0, rate=1.0, snr_db=10.0)

    files = {"file": ("practice.wav", wav_bytes(clip.audio), "audio/wav")}
    resp = client.post("/api/clips", params={"reference_id": reference["id"]}, files=files)

    assert resp.status_code == 422
    detail = resp.json()["detail"]
    assert detail["error"] == "clip_too_short"
    assert detail["duration_sec"] == pytest.approx(5.0, abs=0.05)
    assert detail["min_sec"] == MIN_CLIP_SEC


def test_clip_just_over_minimum_aligns(client):
    ref_audio = make_reference(duration_sec=60.0, seed=18)
    reference = upload_reference(client, ref_audio)
    clip = make_clip(ref_audio, start_sec=10.0, duration_sec=MIN_CLIP_SEC + 0.5, rate=1.0, snr_db=10.0)

    body = upload_clip(client, reference["id"], clip.audio)

    assert len(clip.audio) / SR > MIN_CLIP_SEC
    assert body["alignment"]["top_candidates"][0]["offset_sec"] == pytest.approx(10.0, abs=0.5)
    assert body["alignment"]["failed"] is False


@pytest.mark.parametrize(
    ("score", "failed"),
    [(MIN_MATCH_SCORE - 0.01, True), (MIN_MATCH_SCORE + 0.01, False)],
)
def test_failed_flag_follows_winner_score(client, monkeypatch, score, failed):
    weak_match = MatchResult(top_candidates=(MatchCandidate(rate=0.75, offset_sec=3.0, score=score, peak_ratio=1.5),))
    monkeypatch.setattr(clip_routes, "align_clip", lambda *args: weak_match)
    reference = upload_reference(client, make_reference(duration_sec=20.0, seed=19))

    body = upload_clip(client, reference["id"], make_reference(duration_sec=5.0, seed=20))
    assert body["alignment"]["failed"] is failed
