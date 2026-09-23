# Layouts: side by side and stacked

> TODO.md: "offer different render (side by side, stacked)"

**Size:** S · **Depends on:** nothing. It's easier after [instant-preview](instant-preview.md), because that makes Download the only render.

## Today

- **The player** shows the reference beside the take on wide screens and above it on narrow ones. A CSS media query decides; the user can't choose.
- **Downloads** are "Your take" and "Side by side". The side-by-side render (`build_side_by_side_command`) scales both videos to 720 px high and puts them next to each other with `hstack`. There's no stacked render.

## Goal

On Watch, the user picks a layout: **Side by side**, **Stacked**, or **Take only**. The player shows that layout, and a single Download button saves exactly what's on screen.

## Key decisions

- **What you see is what you download.** The two download buttons become one, which renders the current layout and sound.
- **`Layout = Literal["take", "side-by-side", "stacked"]`** in `server/models.py`. `layout` is already a `RenderParams` field, so the cache needs nothing new. `_download_name` needs a third case (`…-stacked.mp4`).
- **One compare command, not two.** `build_side_by_side_command` becomes `build_compare_command(..., layout)`. The two layouts differ only in their fit filter and their stack filter:
  - side by side: `scale=-2:{COMPARE_HEIGHT}` then `hstack` (same height)
  - stacked: `scale={COMPARE_WIDTH}:-2` then `vstack` (same width)

  The `-2` keeps the free dimension even, which `yuv420p` requires.
- **Config:** `SIDE_BY_SIDE_HEIGHT` and `SIDE_BY_SIDE_FPS` become `COMPARE_HEIGHT`, `COMPARE_WIDTH`, and `COMPARE_FPS`. With a stacked width of 720, a landscape reference (720×405) over a portrait take (720×1280) makes a 720×1685 video. That's tall on purpose, for phones.
- **The reference always comes first,** on the left or on top. Swapping the order is out of scope.
- **The default layout** is side by side on wide screens and stacked on narrow ones, which matches today. The user's pick is kept in `App` state, so it carries over to the next take in the same session.
- **An audio-only reference** has only one layout, Take only, so the picker is hidden.
- **CSS:** a layout class on `.compare` (`.side-by-side` for a row, `.stacked` for a column) replaces the media query. Side by side on a portrait phone comes out small, but that's what the user picked.

## What to build

```
dancesync/config.py     COMPARE_* constants
dancesync/sync.py       build_compare_command / render_compare (replaces the side-by-side pair)
server/models.py        Layout gains "stacked"
server/routes/synced.py _download_name for stacked
server/worker.py        dispatch on layout
web/src/components/
  LayoutToggle.jsx      a Segmented control (shared with Sound; see review-speed.md)
  ComparePlayer.jsx     a layout class instead of the media query
  WatchStep.jsx         one DownloadButton for the current layout + sound
web/src/styles.css
```

## Tests

- `test_sync.py`: the stacked command uses `vstack` and `scale=720:-2`. A rendered stacked output is 720 wide, and its height is the sum of the two scaled heights (checked with ffprobe).
- `test_api_synced.py`: `layout=stacked` renders, an unknown layout returns 422, and the download name ends in `-stacked.mp4`.
- `flow.test.js`: the default layout for each combination of viewport width and reference type.

## Acceptance criteria

- All three layouts preview and download, and each download matches its preview
- Stacked plays in a browser `<video>` (even dimensions, baseline profile)
- With an audio-only reference, only the take is offered, as today
