# DS-28 — `stacked` through the API

**Track:** Layouts · **Size:** XS · **Depends on:** [DS-03](DS-03-render-params-record.md), [DS-27](DS-27-compare-command.md) · **Spec:** [layouts.md](../specs/layouts.md)

## Scope

- `Layout = Literal["take", "side-by-side", "stacked"]` in `server/models.py`.
- `server/worker.py` dispatches on layout; `_download_name` gains the third case (`…-stacked.mp4`).
- Layout is already part of the cache name via DS-03's record, so nothing new there.

## Acceptance criteria

- `layout=stacked` renders and serves
- An unknown layout returns 422
- The download filename ends in `-stacked.mp4`
