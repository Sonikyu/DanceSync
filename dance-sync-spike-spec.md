# Dance Sync — Alignment Spike

**Purpose:** Answer one question before committing a semester to the full build.

> Does a phone recording of a laptop speaker — in a real room, with real noise, at 0.75x playback — retain enough musical structure to be matched against the original reference?

If no, there is no project. Find out in a weekend.

**This is a throwaway experiment, not a prototype.** No code from it ships.

---

## Out of scope

Explicitly not part of this spike:

- No server, no FastAPI, no Docker, no cloud
- No UI, no upload flow, no client of any kind
- No video handling — audio only
- No millisecond-precision measurement (that's the week-8 benchmark harness)
- No optimization

If you find yourself installing FastAPI, stop. That's the spike becoming the project.

---

## Materials

| Item | Detail |
|---|---|
| Songs | 3, from your intended reference library |
| — one must have | copy-pasted / near-identical repeated choruses |
| Reference source | Local audio files, full length |
| Playback | Laptop speaker |
| Capture | Phone, native camera app, across the room |
| Tools | Python + librosa + numpy + matplotlib, Audacity |

---

## Tier A — synthetic (do this first, ~1 hour)

Tests your **code**, not the world. Ground truth is exact.

1. Load a reference file.
2. Cut a 30s chunk from a known mid-song position.
3. Time-stretch the chunk to 0.75x; add white noise at moderate SNR.
4. Run the matcher against the full reference.

**Gate:** recovers the correct rate and lands within ~50 ms. Do not proceed to Tier B until this is clean — a failure here is a bug (indexing, normalization, feature-frame conversion), and you don't want to debug it with real recordings in the mix.

---

## Tier B — real recordings (~1 hour filming)

Six clips, **30–45s each, all starting mid-song.**

| # | Rate | Condition |
|---|---|---|
| 1 | 1.0x | Room A (hard surfaces — kitchen, bathroom) |
| 2 | 1.0x | Room B (soft surfaces — carpet, bedroom) |
| 3 | 0.75x | Room A |
| 4 | 0.75x | Room B |
| 5 | 0.75x | With TV or conversation audible |
| 6 | 0.75x | Repeated-chorus song, **started at the 2nd chorus** |

### Ground truth

Open clip and reference in Audacity. Find a sharp transient visible in both waveforms. Read off both timestamps, subtract.

Two minutes per clip, accurate to well under 0.1s. That's sufficient — this spike distinguishes "right place" from "random place," not fine precision.

---

## Method

Core logic, ~30 lines inside a ~150-line script:

```python
def match(clip_audio, ref_audio, rates=(1.0, 0.75, 0.5)):
    clip_f = normalize(librosa.feature.chroma_cqt(y=clip_audio, sr=SR))
    best = None
    for rate in rates:
        stretched = librosa.effects.time_stretch(ref_audio, rate=rate)
        ref_f = normalize(librosa.feature.chroma_cqt(y=stretched, sr=SR))
        scores = sliding_correlation(clip_f, ref_f)   # FFT per bin, summed
        peak = scores.argmax()
        runner_up = best_peak_outside(scores, exclude_around=peak)
        if best is None or scores[peak] > best.score:
            best = Result(rate, frames_to_sec(peak), scores[peak],
                          ratio=scores[peak] / runner_up)
    return best
```

**Two details that matter more than they look:**

- `normalize` — z-score each feature dimension over time, so loudness differences between rooms don't dominate the correlation.
- `sliding_correlation` — divide by overlap length at each position. Without this, short-overlap positions are unfairly penalized and results cluster toward the middle of the reference.

**Output per clip:** `rate, offset_sec, peak_ratio`, plus a plot of the score curve.

Also worth logging: whether the correct answer appears in the top 3 peaks, even when the top 1 is wrong.

---

## Pass criteria

| Clip | Passes if |
|---|---|
| 1, 2 (1.0x) | Rate = 1.0, offset within ~0.1s |
| 3, 4 (0.75x) | **Rate = 0.75, offset within ~0.2s** ← the real test |
| 5 (noisy) | Behaves comparably to clips 3–4 |
| 6 (repeated chorus) | Several near-equal peaks; true answer in top 3; `peak_ratio` visibly lower than clips 1–5 |

Clip 6 is **not** scored on getting it right first try. It's scored on whether the ambiguity is *detectable* — that's what drives the top-3-thumbnails fallback UX.

---

## Decision table

| Result | Meaning | Action |
|---|---|---|
| All pass | Premise holds | Proceed to full build as planned |
| 1.0x works, 0.75x fails | Time-stretch artifacts worse than expected | Try onset envelope alongside chroma; finer rate grid; else scope v1 to full-speed only |
| Only noisy clip fails | Noise is the binding constraint | Band-limit features; consider fingerprint-style matcher |
| All Tier B fails, Tier A passed | Recording chain destroying signal | Check phone audio preprocessing / AGC; re-record with different settings |
| Tier A fails | Bug in your code | Debug before touching Tier B |

---

## Budget

| Task | Time |
|---|---|
| Tier A setup + run | ~1 hr |
| Filming Tier B | ~1 hr |
| Ground-truth labeling | ~15 min |
| librosa implementation | 4–6 hrs (first time) |
| **Total** | **One weekend** |

---

## Deliverable

A table of six rows — `clip, true_offset, predicted_offset, error, predicted_rate, peak_ratio` — and six score-curve plots.

That's it. Then decide.
