"""Route tests for GET /api/clips/{id}/synced: upload -> align -> render."""

from __future__ import annotations

import shutil
import subprocess

import pytest
import soundfile as sf

from dancesync import audio, matcher
from dancesync.config import SR
from server.routes import synced as synced_routes
from tests.conftest import (
    flash_time_sec,
    make_clip,
    make_reference,
    upload_clip,
    upload_reference,
    write_flash_video,
)

needs_ffmpeg = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")


@needs_ffmpeg
def test_synced_video_lines_up_with_reference(client, tmp_path):
    ref_audio = make_reference(duration_sec=60.0, seed=6)
    reference = upload_reference(client, ref_audio)

    # A 0.75x practice recording of reference 10-25 s: 20 s long, flash at 4 s.
    clip = make_clip(ref_audio, start_sec=10.0, duration_sec=15.0, rate=0.75, snr_db=10.0)
    clip_audio_path = tmp_path / "practice.wav"
    sf.write(str(clip_audio_path), clip.audio, SR)
    video_path = tmp_path / "practice.mov"
    write_flash_video(video_path, len(clip.audio) / SR, flash_sec=4.0, audio_path=clip_audio_path)

    files = {"file": ("practice.mov", video_path.read_bytes(), "video/quicktime")}
    upload = client.post("/api/clips", params={"reference_id": reference["id"]}, files=files)
    assert upload.status_code == 201, upload.text

    resp = client.get(f"/api/clips/{upload.json()['id']}/synced")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "video/mp4"
    synced_path = tmp_path / "synced.mp4"
    synced_path.write_bytes(resp.content)

    # Back at original speed: 15 s long, flash at 4 s * 0.75, and the audio is
    # the reference itself from 10 s on.
    synced_audio = audio.decode(synced_path, use_cache=False)
    assert audio.duration_sec(synced_audio) == pytest.approx(15.0, abs=0.1)
    assert flash_time_sec(synced_path) == pytest.approx(3.0, abs=0.05)
    assert matcher.match(synced_audio, ref_audio, rates=(1.0,)).offset_sec == pytest.approx(
        10.0, abs=0.1
    )

    # Served from cache: a re-render would rename a new file into place.
    rendered = list((tmp_path / "media" / "synced").glob("*.mp4"))
    inode = rendered[0].stat().st_ino
    client.get(f"/api/clips/{upload.json()['id']}/synced")
    assert [p.stat().st_ino for p in rendered] == [inode]


def test_synced_uses_selected_candidate(client, monkeypatch):
    ref_audio = make_reference(duration_sec=60.0, seed=7)
    reference = upload_reference(client, ref_audio)
    clip = make_clip(ref_audio, start_sec=30.0, duration_sec=15.0, rate=1.0, snr_db=10.0)
    body = upload_clip(client, reference["id"], clip.audio)

    rendered = {}

    def fake_sync_clip(clip_path, reference_path, params, out_path):
        rendered.update(rate=params.rate, offset_sec=params.offset_sec)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(b"not really an mp4")

    monkeypatch.setattr(synced_routes, "sync_clip", fake_sync_clip)
    client.post(f"/api/clips/{body['id']}/select", json={"index": 1})
    resp = client.get(f"/api/clips/{body['id']}/synced")

    assert resp.status_code == 200
    chosen = body["alignment"]["top_candidates"][1]
    assert rendered == {"rate": chosen["rate"], "offset_sec": chosen["offset_sec"]}


def test_synced_head_renders_without_sending_the_video(client, monkeypatch):
    ref_audio = make_reference(duration_sec=60.0, seed=9)
    reference = upload_reference(client, ref_audio)
    clip = make_clip(ref_audio, start_sec=30.0, duration_sec=15.0, rate=1.0, snr_db=10.0)
    body = upload_clip(client, reference["id"], clip.audio)
    fake_video = b"not really an mp4"

    def fake_sync_clip(clip_path, reference_path, params, out_path):
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(fake_video)

    monkeypatch.setattr(synced_routes, "sync_clip", fake_sync_clip)
    resp = client.head(f"/api/clips/{body['id']}/synced")

    assert resp.status_code == 200
    assert resp.content == b""
    assert resp.headers["content-length"] == str(len(fake_video))   # the render ran


def test_synced_sound_and_layout_pick_the_render(client, monkeypatch):
    ref_audio = make_reference(duration_sec=60.0, seed=10)
    reference = upload_reference(client, ref_audio)
    clip = make_clip(ref_audio, start_sec=20.0, duration_sec=15.0, rate=1.0, snr_db=10.0)
    body = upload_clip(client, reference["id"], clip.audio)
    renders = []

    def fake_sync_clip(clip_path, reference_path, params, out_path):
        renders.append((params.sound, params.layout, out_path.name))
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(b"not really an mp4")

    monkeypatch.setattr(synced_routes, "sync_clip", fake_sync_clip)
    default = client.get(f"/api/clips/{body['id']}/synced")
    room_side = client.get(
        f"/api/clips/{body['id']}/synced", params={"sound": "room", "layout": "side-by-side"}
    )

    assert [(sound, layout) for sound, layout, _ in renders] == [
        ("song", "take"), ("room", "side-by-side"),
    ]
    assert renders[0][2] != renders[1][2]   # cached separately
    assert 'filename="practice-synced.mp4"' in default.headers["content-disposition"]
    assert 'filename="practice-side-by-side-room.mp4"' in room_side.headers["content-disposition"]


def test_synced_unknown_sound_rejected(client):
    resp = client.get("/api/clips/anything/synced", params={"sound": "karaoke"})
    assert resp.status_code == 422


@needs_ffmpeg
def test_synced_audio_only_clip_rejected(client):
    ref_audio = make_reference(duration_sec=60.0, seed=8)
    reference = upload_reference(client, ref_audio)
    clip = make_clip(ref_audio, start_sec=5.0, duration_sec=15.0, rate=1.0, snr_db=10.0)
    body = upload_clip(client, reference["id"], clip.audio)

    resp = client.get(f"/api/clips/{body['id']}/synced")
    assert resp.status_code == 422
    assert "no video stream" in resp.json()["detail"]


def test_synced_unknown_clip_404s(client):
    assert client.get("/api/clips/nope/synced").status_code == 404


@needs_ffmpeg
def test_synced_stacked_renders_and_serves(client, tmp_path):
    ref_audio = make_reference(duration_sec=60.0, seed=23)
    song_path = tmp_path / "song.wav"
    sf.write(str(song_path), ref_audio, SR)
    choreography = tmp_path / "choreography.mp4"
    write_flash_video(choreography, 60.0, flash_sec=30.0, audio_path=song_path, size="160x90")
    files = {"file": ("choreography.mp4", choreography.read_bytes(), "video/mp4")}
    reference = client.post("/api/references", files=files).json()

    clip = make_clip(ref_audio, start_sec=20.0, duration_sec=15.0, rate=1.0, snr_db=10.0)
    clip_audio_path = tmp_path / "practice.wav"
    sf.write(str(clip_audio_path), clip.audio, SR)
    video_path = tmp_path / "practice.mp4"
    write_flash_video(video_path, len(clip.audio) / SR, flash_sec=4.0, audio_path=clip_audio_path)
    files = {"file": ("practice.mp4", video_path.read_bytes(), "video/mp4")}
    clip_id = client.post("/api/clips", params={"reference_id": reference["id"]}, files=files).json()["id"]

    resp = client.get(f"/api/clips/{clip_id}/synced", params={"layout": "stacked"})
    assert resp.status_code == 200
    assert 'filename="practice-stacked.mp4"' in resp.headers["content-disposition"]
    stacked_path = tmp_path / "stacked.mp4"
    stacked_path.write_bytes(resp.content)
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v", "-show_entries", "stream=width,height",
         "-of", "csv=p=0", str(stacked_path)],
        capture_output=True, text=True, check=True,
    )
    assert probe.stdout.strip() == "720,1126"   # a 16:9 reference (720x406) over the square take


def test_synced_unknown_layout_rejected(client):
    resp = client.get("/api/clips/anything/synced", params={"layout": "diagonal"})
    assert resp.status_code == 422
