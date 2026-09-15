# Takes at any practice speed

> TODO.md: "playback speed". This is part 2 of 2: the matcher. Part 1 is [review-speed.md](review-speed.md). The manual version of this is [manual-alignment.md](manual-alignment.md).

**Size:** M · **Depends on:** nothing. It changes the matcher, so the Tier A gate is the bar.

## Problem

The matcher only tries three playback rates: `RATES = (1.0, 0.75, 0.5)`. YouTube's custom speed setting moves in 0.05 steps, and practice apps go down to 1% steps. A take filmed at 0.8× today gets matched at 0.75×, if it matches at all. Even when the offset comes out right, the render drifts: by the end of a one-minute take, it's 3 s out.

The sync error at the end of a take is the clip duration × the rate error. Keeping that under 0.1 s for a 60 s clip means getting the rate within ±0.0017, which is finer than any grid worth searching. So the plan has two steps: find the take on a coarser grid, then measure its exact rate.

## Approach

### 1. Coarse grid

`RATES` becomes 0.50 to 1.00 in steps of 0.05, which is 11 rates. The matching algorithm stays the same.

- **First, check with Tier A that a peak still shows up when the rate is up to 0.025 off.** Chroma changes slowly (a chord usually lasts half a second or more), so it probably does for 30–60 s clips. If it doesn't, use steps of 0.025.
- **Remove duplicate candidates across rates.** `match` gathers candidates from every rate and keeps the three highest-scoring. Neighboring rates find the same passage, so on a fine grid the top 3 would be one chorus at three adjacent rates, pushing the second chorus off the list. That would break the Match screen and `test_ambiguity.py`. Merge candidates whose original-timeline offsets are within `PEAK_EXCLUDE_SEC` of each other, keeping the best score.

### 2. Measure the rate from drift

Match the first half and the second half of the clip separately, at the rate that won the coarse search. Search each half only within ±`PEAK_EXCLUDE_SEC` of where the coarse match placed it, so a half can't jump to the other chorus. Both offsets are in the original timeline, so:

```
rate = (offset_b - offset_a) / (start_b - start_a)
```

Here `start_a` and `start_b` are where each half starts in the clip: 0 and L/2.

- **Using halves of equal length cancels out the coarse rate's error.** A sub-clip matched at a slightly wrong rate lines up best around its middle, so its estimated start shifts by `(true_rate - coarse_rate) × half_len / 2`. Both halves shift by the same amount, so their difference isn't affected.
- **No new stretches are needed.** The halves are compared against the coarse rate's cached features, so only the correlation runs again, and that's cheap next to stretching.
- **Correct each candidate's offset for the refined rate** using the same model: `offset -= (refined - coarse) × clip_len / 2`. Check the model against synthetic clips with a known offset. If it isn't accurate enough, run `match` once more at the refined rate instead, at the cost of stretching the whole song again for every clip.
- **Snap to round speeds.** Players use round speeds, so if the refined rate is within `RATE_SNAP_TOL` (0.003) of a multiple of 0.01, snap to it. Either way, round the stored rate to 4 decimals so render filenames and the UI stay tidy.
- **Skip refinement for short clips.** Below `MIN_REFINE_CLIP_SEC` (about 20 s), each half is too short to match reliably, and the halves are too close together to measure the rate. Keep the coarse rate.

Put the rate refinement in its own module, `dancesync/rate.py`, because `matcher.py` is already 207 lines.

## Cost

Stretching the song is the slow part: tens of seconds per rate, according to the docstring of `precompute_ref_features`. Going from 2 stretched rates to 10 would make the first take against a new song take minutes instead of seconds. Measure it first, then:

- **Compute only the missing rates.** Today, if the cache file lacks any requested rate, `precompute_ref_features` recomputes every rate. Merge the new rates into the file instead, so adding to `RATES` doesn't throw away earlier work.
- **Start stretching as soon as the song is uploaded,** in a process pool. That way it runs while the dancer is filming or uploading the take. If it isn't finished when the clip is uploaded, the clip upload waits for it. This is a small first step toward Phase 5's job queue.
- **Worth one experiment: stretch the clip instead of the reference.** This is the `--stretch clip` option the spike put off.
  - The cost scales with the clip (30–60 s) rather than the song, and there's nothing to cache.
  - Offsets come out directly in the original timeline, with no `× rate` conversion.
  - It hasn't been tested on real recordings. Tier A and Tier B decide.

## Tests

- **Tier A at off-grid rates:** 0.7, 0.8, 0.85, and 0.9, at the usual positions and noise levels (SNRs). The rate must be within ±0.005 and the offset within 50 ms.
- The existing 1.0, 0.75, and 0.5 cases keep passing unchanged, and `test_ambiguity.py` still offers both choruses.
- **Unit tests for `dancesync/rate.py`:** the drift formula, and the error cancellation on synthetic clips; snapping; skipping short clips.
- **Keep the suite fast:** tests that aren't about rates pass `rates=` explicitly.

## Acceptance criteria

- A synthetic 60 s take at 0.8× renders with less than 100 ms of drift at the end
- At least one real phone recording at 0.8× or 0.9× matches and renders in sync (Tier B)
- The time for a first alignment against a new 3–4 min song is measured and written down in the PR
- `formatRate` rounds refined rates for display ("0.8× speed", "0.83× speed")
