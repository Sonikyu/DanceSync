# DS-15 — Serve the uploaded clip bytes

**Track:** Instant preview · **Size:** S · **Depends on:** nothing · **Spec:** [instant-preview.md](../specs/instant-preview.md)

## Context

The browser can only play the raw take instead of a render if it can fetch the raw take. This mirrors `GET /api/references/{id}/media`, which already exists.

## Scope

- `GET /api/clips/{id}/media` in `server/routes/clips.py`, the same shape as the references route: `FileResponse`, correct content type, 404 for an unknown id.
- Range requests must work, so a 500 MB clip can be seeked without downloading it whole. `FileResponse` handles this; the tests must prove it.

## Acceptance criteria

- The endpoint returns the stored bytes for a known clip and 404 otherwise
- A `Range` request returns 206 with the right slice and `Content-Range`
- `tests/test_api.py` covers all three
