"""YouTube import: link validation, the metadata checks, and the import route.
Offline: a fake yt-dlp stands in for the real one, answering `-J` with
metadata and a download by copying a small fixture MP4 into place."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys

import pytest

from dancesync.config import SR
from server import youtube
from server.config import MAX_IMPORT_DURATION_SEC
from tests.conftest import wav_bytes, write_flash_video

VIDEO_ID = "abcDEF12345"


@pytest.mark.parametrize("url", [
    f"https://www.youtube.com/watch?v={VIDEO_ID}",
    f"https://youtube.com/watch?v={VIDEO_ID}&t=30s",
    f"https://m.youtube.com/watch?v={VIDEO_ID}",
    f"https://www.youtube.com/shorts/{VIDEO_ID}",
    f"https://youtu.be/{VIDEO_ID}?si=share",
    f"  http://youtu.be/{VIDEO_ID}  ",
])
def test_accepted_links_give_the_video_id(url):
    assert youtube.parse_video_id(url) == VIDEO_ID


@pytest.mark.parametrize("url", [
    f"https://youtube.com.evil.com/watch?v={VIDEO_ID}",
    f"https://evil.com/?youtube.com/watch?v={VIDEO_ID}",
    f"https://evil.com/watch?v={VIDEO_ID}#youtu.be",
    "http://localhost/watch?v=abcDEF12345",
    f"file://youtu.be/{VIDEO_ID}",
    f"https://www.youtube.com/playlist?list={VIDEO_ID}",
    "https://www.youtube.com/watch?v=short",
    "https://youtu.be/",
    "not a url",
])
def test_other_links_are_rejected(url):
    with pytest.raises(youtube.YouTubeError) as exc:
        youtube.parse_video_id(url)
    assert exc.value.status == 400


def test_yt_dlp_runs_from_this_python(monkeypatch):
    seen = []
    monkeypatch.setattr(youtube.subprocess, "run", lambda cmd, **kw: seen.append(cmd))
    youtube._run_yt_dlp(["-J", youtube.watch_url(VIDEO_ID)])
    assert seen[0][:3] == [sys.executable, "-m", "yt_dlp"]
    assert "--no-playlist" in seen[0]


@pytest.mark.parametrize("info, status", [
    ({"is_live": True}, 422),
    ({"live_status": "is_upcoming"}, 422),
    ({"age_limit": 18}, 422),
    ({"availability": "private"}, 422),
    ({"duration": MAX_IMPORT_DURATION_SEC + 1}, 413),
])
def test_probe_rejects_what_cant_be_imported(fake_yt_dlp, info, status):
    fake_yt_dlp.info.update(info)
    with pytest.raises(youtube.YouTubeError) as exc:
        youtube.probe(VIDEO_ID)
    assert exc.value.status == status


@pytest.mark.parametrize("stderr, message", [
    (b"ERROR: [youtube] abcDEF12345: Private video. Sign in if you've been granted access",
     "private videos can't be imported"),
    (b"ERROR: [youtube] abcDEF12345: Sign in to confirm your age. This video may be inappropriate",
     "age-restricted videos can't be imported"),
])
def test_probe_names_private_and_age_restricted_failures(fake_yt_dlp, stderr, message):
    fake_yt_dlp.probe_stderr = stderr
    with pytest.raises(youtube.YouTubeError, match=message):
        youtube.probe(VIDEO_ID)


@pytest.mark.parametrize("title, filename", [
    ("BLACKPINK - 'How You Like That' Dance Practice", "BLACKPINK - 'How You Like That' Dance Practice.mp4"),
    ("../../etc/passwd", "etcpasswd.mp4"),
    ("///", f"{VIDEO_ID}.mp4"),
])
def test_safe_filename(title, filename):
    assert youtube.safe_filename(title, VIDEO_ID) == filename


def test_import_creates_a_reference_with_video(client, fake_yt_dlp):
    resp = client.post("/api/references/import", json={"url": f"https://youtu.be/{VIDEO_ID}"})
    assert resp.status_code == 201, resp.text
    reference = resp.json()
    assert reference["filename"] == "Dance Practice.mp4"
    assert reference["source_url"] == youtube.watch_url(VIDEO_ID)
    assert reference["duration_sec"] == pytest.approx(20.0, abs=0.1)

    media = client.get(f"/api/references/{reference['id']}/media")
    assert media.status_code == 200
    assert media.content == fake_yt_dlp.video_bytes
    assert [r["id"] for r in client.get("/api/references").json()] == [reference["id"]]


def test_repeat_import_returns_the_same_reference_without_downloading(client, fake_yt_dlp):
    first = client.post("/api/references/import", json={"url": f"https://youtu.be/{VIDEO_ID}"})
    again = client.post("/api/references/import", json={"url": f"https://www.youtube.com/watch?v={VIDEO_ID}"})
    assert again.status_code == 200
    assert again.json() == first.json()
    assert fake_yt_dlp.downloads == 1


def test_non_youtube_link_never_reaches_yt_dlp(client, fake_yt_dlp):
    resp = client.post("/api/references/import", json={"url": "http://localhost:8000/secret"})
    assert resp.status_code == 400
    assert fake_yt_dlp.calls == 0


def test_too_long_video_is_rejected_before_downloading(client, fake_yt_dlp):
    fake_yt_dlp.info["duration"] = MAX_IMPORT_DURATION_SEC + 60
    resp = client.post("/api/references/import", json={"url": f"https://youtu.be/{VIDEO_ID}"})
    assert resp.status_code == 413
    assert fake_yt_dlp.downloads == 0


def test_video_over_the_size_limit_is_rejected(client, fake_yt_dlp):
    fake_yt_dlp.skip_download = True   # what yt-dlp does past --max-filesize
    resp = client.post("/api/references/import", json={"url": f"https://youtu.be/{VIDEO_ID}"})
    assert resp.status_code == 413
    assert client.get("/api/references").json() == []


def test_download_failure_reports_yt_dlp_error(client, fake_yt_dlp):
    fake_yt_dlp.download_stderr = b"WARNING: retrying\nERROR: HTTP Error 403: Forbidden"
    resp = client.post("/api/references/import", json={"url": f"https://youtu.be/{VIDEO_ID}"})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "yt-dlp failed: ERROR: HTTP Error 403: Forbidden"


def test_missing_yt_dlp_is_503(client, fake_yt_dlp, monkeypatch):
    monkeypatch.setattr(youtube, "is_installed", lambda: False)
    resp = client.post("/api/references/import", json={"url": f"https://youtu.be/{VIDEO_ID}"})
    assert resp.status_code == 503


@pytest.mark.network
def test_real_import(client):
    """Downloads "Me at the zoo" (19 s) for real. Run with `-m network`."""
    resp = client.post("/api/references/import", json={"url": "https://youtu.be/jNQXAC9IVRw"})
    assert resp.status_code == 201, resp.text
    assert resp.json()["duration_sec"] == pytest.approx(19, abs=1)


class FakeYtDlp:
    """Answers `_run_yt_dlp` the way yt-dlp would, and counts its calls."""

    def __init__(self, video_path):
        self.video_bytes = video_path.read_bytes()
        self.video_path = video_path
        self.info = {"id": VIDEO_ID, "title": "Dance Practice", "duration": 20, "live_status": "not_live"}
        self.probe_stderr = None
        self.download_stderr = None
        self.skip_download = False
        self.calls = 0
        self.downloads = 0

    def __call__(self, args):
        self.calls += 1
        if "-J" in args:
            return self._probe()
        self.downloads += 1
        return self._download(args)

    def _probe(self):
        if self.probe_stderr:
            return subprocess.CompletedProcess([], 1, b"", self.probe_stderr)
        return subprocess.CompletedProcess([], 0, json.dumps(self.info).encode(), b"")

    def _download(self, args):
        if self.download_stderr:
            return subprocess.CompletedProcess([], 1, b"", self.download_stderr)
        if not self.skip_download:
            out_template = args[args.index("-o") + 1]
            shutil.copy(self.video_path, out_template.replace("%(ext)s", "mp4"))
        return subprocess.CompletedProcess([], 0, b"", b"")


@pytest.fixture(scope="session")
def imported_video(tmp_path_factory, reference_audio):
    """A 20 s MP4 with the song's opening as its soundtrack."""
    tmp = tmp_path_factory.mktemp("youtube")
    audio_path = tmp / "song.wav"
    audio_path.write_bytes(wav_bytes(reference_audio[: 20 * SR]))
    video_path = tmp / "practice.mp4"
    write_flash_video(video_path, duration_sec=20, flash_sec=5, audio_path=audio_path)
    return video_path


@pytest.fixture
def fake_yt_dlp(monkeypatch, imported_video):
    fake = FakeYtDlp(imported_video)
    monkeypatch.setattr(youtube, "_run_yt_dlp", fake)
    return fake
