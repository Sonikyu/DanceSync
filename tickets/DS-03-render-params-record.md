# DS-03 — One render-params record, serialized in one place

**Track:** Foundations · **Size:** S · **Depends on:** nothing · **Unblocks:** DS-23, DS-28, DS-36, and every later feature that changes the picture or the audio

## Context

Invariant 7 says a render's cache name must encode every input, on the server (`_synced_id` in `routes/synced.py`) and in the browser (`api.syncedVideoUrl`). Both are hand-rolled string builders that must be kept in step by hand. Five queued features — manual alignment, layouts, review speed, editing, practice speeds — each add a field to both. The failure mode is silent: a stale file that looks like a working render.

Doing this once, before those five, is cheaper than reviewing the same two-sided edit five times.

## Scope

- `server/models.py`: a `RenderParams` record holding everything a render depends on today — clip id, reference id, rate, offset, layout, sound.
- One function that turns it into the cache id, and one that turns it into the query string. `_synced_id` and the `/synced` route read from the record instead of assembling fields.
- `web/src/api.js`: `syncedVideoUrl(params)` builds its query from the same field list, with the field names in one exported constant.
- A test that asserts the server's cache id and the browser's query string cover the same field set, so adding a field on one side without the other fails CI.

## Out of scope

Changing any rendered output. This is a pure refactor: existing cache filenames may change, but a fresh render of the same inputs must be byte-identical.

## Acceptance criteria

- Renders are unchanged byte for byte
- Adding a field to `RenderParams` without adding it to the browser's list fails a test
- `routes/synced.py` no longer builds the cache name from inline string pieces
