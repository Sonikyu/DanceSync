# DS-32 — Paste a YouTube link on the Song step

**Track:** YouTube import · **Size:** XS · **Depends on:** [DS-31](DS-31-youtube-import-route.md) · **Spec:** [youtube-import.md](../specs/youtube-import.md)

## Scope

- A "Paste a YouTube link" field below the drop zone in the Song step. Submitting shows a "Downloading from YouTube…" spinner, then calls `onPick(reference)` exactly as an upload does.
- Dancer-facing messages in `api.js` for 400, 413, and 422.
- No progress bar in v1; yt-dlp can report progress with `--newline`, but showing it needs DS-14.

## Acceptance criteria

- Import and upload land in the same place in the flow
- Each error status produces a message that says what to do next
