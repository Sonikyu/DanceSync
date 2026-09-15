# YouTube import

> TODO.md: "youtube url scraping"

**Size:** S–M · **Depends on:** nothing, but Phase 5 access control should land before the server is reachable from the internet.

## Goal

On the Song step, the user can paste a YouTube link instead of uploading a file. It's usually a link to a dance practice video. The server downloads the video, and it becomes a normal reference with its picture included, so side by side works.

## Scope decision

DanceSync is for its owner and friends, run locally or self-hosted, so downloading on the server with `yt-dlp` is a reasonable fit. YouTube's terms don't permit downloading. The owner accepts that risk for personal use, but it rules this feature out if DanceSync ever becomes a public site.

YouTube also blocks many datacenter IP addresses with "confirm you're not a bot" checks. Imports that work from a home machine may fail from a VPS, so check this before choosing a host.

## Key decisions

- **Run `yt-dlp` as a subprocess, the same way we run ffmpeg,** rather than importing it as a Python library.
  - Call it as `[sys.executable, "-m", "yt_dlp", …]` instead of relying on `PATH`. That way the server always uses the venv's copy, and `pip install -U yt-dlp` updates it.
  - Add `yt-dlp` to `pyproject.toml`. YouTube changes break it every few weeks, so updating it is a documented chore.
  - It merges video and audio streams with ffmpeg, which we already require.
- **Accept only YouTube URLs:** `youtube.com/watch`, `youtube.com/shorts`, `m.youtube.com`, and `youtu.be`. Check the host before calling yt-dlp. yt-dlp supports thousands of sites plus plain HTTP, so without an allowlist the server would fetch whatever URL it's given. Other sites such as TikTok or Instagram can be added later, one allowlist entry each.
- **Check the metadata before downloading.** `yt-dlp -J --no-playlist` fetches metadata without downloading anything.
  - Reject live streams and anything longer than `MAX_IMPORT_DURATION_SEC` (15 min).
  - Reject private and age-restricted videos with a clear message.
- **Download up to 1080p H.264 with AAC audio, merged into an MP4,** so every browser plays it without transcoding.
  - Don't cap at 720p: zooming in on one dancer ([video-editing](video-editing.md), [follow-dancer](follow-dancer.md)) needs the pixels.
  - A 4-minute 1080p video can go over the 100 MB upload limit, so imports get their own limit, `MAX_IMPORT_BYTES` (300 MB), passed to yt-dlp as `--max-filesize`.
- **Recognize repeat imports by YouTube video id, not by content hash.** Two downloads of the same video aren't guaranteed to be byte-identical.
  - `Reference` gains `source_url: str | None = None`.
  - Before downloading, look for an existing reference with the same video id, and return it if one exists.
  - The reference id is still the content hash of the downloaded bytes, so storage keys don't change.
- **The filename is the video title plus `.mp4`, sanitized,** so the song list shows the title.
- **Storage:** `LocalStorage.save` takes an `UploadFile`. Add `save_file(kind, src_path, filename)`, which hashes an already-downloaded file and moves it into place. yt-dlp downloads into a temp directory under the storage root, on the same filesystem, so the move is a rename.
- **v1 imports in a single blocking POST,** the same way clip alignment works.
  - A download takes 5–30 s on home broadband, shown as a "Downloading from YouTube…" spinner with no progress bar.
  - yt-dlp can print its progress with `--newline`, but showing it needs Phase 5's progress channel.
- **The yt-dlp code goes in `server/youtube.py`, not `dancesync/`.** The `dancesync` package handles matching and sync, and fetching media is the server's job.

## API

```
POST /api/references/import   {"url": "https://youtu.be/…"}
  201 → Reference (new)      200 → Reference (already imported)
  400 not a YouTube URL      413 too long / too big
  422 yt-dlp failed (last stderr line, like SyncError)
  503 yt-dlp not installed
```

## UI

The Song step gets a "Paste a YouTube link" field below the drop zone. Submitting it shows the spinner, then calls `onPick(reference)`, just like an upload does. `api.js` gets dancer-friendly messages for 400, 413, and 422.

## Tests

- **URL validation:**
  - Accept `youtube.com/watch?v=…`, `youtu.be/…`, `m.youtube.com`, and shorts links.
  - Reject `youtube.com.evil.com`, `evil.com/?youtube.com`, and `http://localhost`.
- **Route tests run offline.** They monkeypatch the subprocess with a fake yt-dlp that writes a small fixture MP4, so the suite never touches the network.
- **Repeat imports:** importing the same video id twice runs only one download.
- **One optional real download,** marked `network` and skipped by default.

## Acceptance criteria

- Pasting a practice-video link creates a reference with video, and side by side works with it
- Pasting the same link again returns the same reference without downloading
- Non-YouTube URLs are rejected before yt-dlp runs
- The pytest suite passes offline
