# DS-31 — Download an import into a reference

**Track:** YouTube import · **Size:** M · **Depends on:** [DS-30](DS-30-youtube-url-validation.md) · **Spec:** [youtube-import.md](../specs/youtube-import.md)

## Context

The import becomes a normal reference with its picture included, so side by side works with it.

## Scope

- Download up to 1080p H.264 + AAC merged to MP4, so every browser plays it without transcoding. Not capped at 720p: zooming in on one dancer needs the pixels. `--max-filesize` at `MAX_IMPORT_BYTES` (300 MB), separate from the 100 MB upload limit.
- `LocalStorage.save_file(kind, src_path, filename)`: hash an already-downloaded file and move it into place. yt-dlp downloads to a temp directory under the storage root, on the same filesystem, so the move is a rename.
- `Reference.source_url: str | None = None`. Repeat imports are recognised by YouTube video id, not content hash — two downloads of the same video aren't guaranteed byte-identical. The reference id stays the content hash of the downloaded bytes.
- The filename is the sanitized video title plus `.mp4`, so the song list shows the title.
- `POST /api/references/import`: 201 new, 200 already imported, 400 not a YouTube URL, 413 too long or too big, 422 yt-dlp failed (last stderr line, like `SyncError`), 503 yt-dlp not installed.
- v1 blocks in the POST, like clip alignment does.

## Acceptance criteria

- A practice-video link creates a reference with video, and side by side works with it
- The same link twice returns the same reference and runs one download
- The pytest suite passes offline; one real-download test is marked `network` and skipped by default
