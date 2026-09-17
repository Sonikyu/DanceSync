# DS-27 — One compare command for both layouts

**Track:** Layouts · **Size:** S · **Depends on:** nothing · **Spec:** [layouts.md](../specs/layouts.md)

## Context

`build_side_by_side_command` scales both videos to 720 px high and joins them with `hstack`. Stacked differs only in its fit filter and its stack filter, so it's one parameter, not a second function.

## Scope

- `dancesync/config.py`: `SIDE_BY_SIDE_HEIGHT` and `SIDE_BY_SIDE_FPS` become `COMPARE_HEIGHT`, `COMPARE_WIDTH`, `COMPARE_FPS`.
- `build_compare_command(..., layout)` / `render_compare` replace the side-by-side pair. Side by side scales `-2:COMPARE_HEIGHT` then `hstack`; stacked scales `COMPARE_WIDTH:-2` then `vstack`. The `-2` keeps the free dimension even, which `yuv420p` requires.
- Both inputs stay on the 60 fps grid, as today.

## Acceptance criteria

- `test_sync.py` asserts the stacked command uses `vstack` and `scale=720:-2`
- A rendered stacked output is 720 wide and its height is the sum of the two scaled heights, checked with ffprobe
- Side-by-side output is byte-identical to before the refactor
