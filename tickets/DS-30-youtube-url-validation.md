# DS-30 — YouTube URL allowlist and metadata probe

**Track:** YouTube import · **Size:** S · **Depends on:** nothing · **Spec:** [youtube-import.md](../specs/youtube-import.md)

## Context

yt-dlp supports thousands of sites plus plain HTTP. Without a host allowlist, this endpoint fetches whatever URL it is handed — including internal addresses. Validation lands before any download code.

## Scope

- `server/youtube.py`: accept only `youtube.com/watch`, `youtube.com/shorts`, `m.youtube.com`, `youtu.be`. Check the parsed host, not a substring.
- Metadata first, with `yt-dlp -J --no-playlist`, invoked as `[sys.executable, "-m", "yt_dlp", …]` so the venv's copy is always used. Reject live streams, anything over `MAX_IMPORT_DURATION_SEC` (15 min), and private or age-restricted videos, each with its own message.
- `yt-dlp` added to `pyproject.toml`, with a note that YouTube breaks it every few weeks and updating it is a chore.

## Acceptance criteria

- `youtube.com.evil.com`, `evil.com/?youtube.com`, and `http://localhost` are all rejected before yt-dlp runs
- All four accepted URL shapes pass
- Tests run offline, with the subprocess monkeypatched
