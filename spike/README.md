# Alignment spike

Throwaway experiment for the question in `../dance-sync-spike-spec.md`: does a phone
recording of a laptop speaker, at 0.75x, retain enough structure to be matched against
the original? **No code here ships.**

Tier A (synthetic) is implemented. Tier B is filming plus running the same matcher over
imported clips — the ingest layer below exists to hold those clips and their ground truth.

## Setup

```bash
bash spike/setup.sh                       # venv + deps + dependency check
brew install ffmpeg                       # needed for .mov / .mp4 / .m4a / .mp3
.venv/bin/python -m spike.tier_a --demo   # smoke test, no music required
```

`--demo` generates a fake song and runs the full pipeline against it. It proves the
install and the plumbing work; it is **not** a Tier A result, because synthetic chords are
far easier to match than real music. Use a real reference for the actual gate.

## Importing material

Video files are accepted as containers only. `ffmpeg` pulls out the audio track and
everything downstream is audio — no frame is ever decoded, so the spec's "audio only"
scope holds.

Accepted: `.mov` `.mp4` `.m4v` `.m4a` `.wav` `.mp3` `.aac` `.flac` `.aiff` `.caf` `.ogg`
`.opus` `.mkv` `.webm` `.avi` `.3gp` `.wma`. iPhone's camera writes `.mov`, Voice Memos
writes `.m4a`, and AirDropped/compressed exports arrive as `.mp4` — all three work.

```bash
P=.venv/bin/python

$P -m spike.ingest doctor                                    # deps, ffmpeg, folder counts
$P -m spike.ingest add ~/Music/song.mp3 --kind reference --name song-a
$P -m spike.ingest add ~/Desktop/IMG_4821.MOV --kind clip \
    --ref song-a --rate 0.75 --condition "Room A, hard surfaces"
$P -m spike.ingest label img-4821 --truth 92.41              # Audacity ground truth
$P -m spike.ingest list
$P -m spike.ingest probe img-4821                            # codec / duration / channels
```

Bulk import: drop files into `data/inbox/`, then

```bash
$P -m spike.ingest scan --kind clip --ref song-a --rate 0.75
```

`scan` moves everything out of the inbox (`--copy` to leave originals). Imported files are
renamed to a slug, recorded in `data/manifest.json` with duration/codec/ground truth, and
decoded lazily at match time — nothing is transcoded on import.

## Running Tier A

```bash
$P -m spike.tier_a                       # the only imported reference, 30 s @ 40% in, 0.75x, 10 dB
$P -m spike.tier_a --ref song-a --start 90 --snr 10
$P -m spike.tier_a --sweep               # 2 positions x {1.0, 0.75} x {clean, 20 dB, 10 dB}
$P -m spike.tier_a --save-clips          # also write the clips as .wav for Audacity
$P -m spike.tier_a --stretch clip        # stretch the clip instead of the reference
```

Exit code is 0 only if every case recovers the correct rate and lands within `--tolerance`
(default 50 ms). Per-case score-curve plots go to `out/plots/`, the table to
`out/results/tier_a.csv`.

## Layout

```
spike/
├── config.py      SR, hop, rates, paths — change parameters here, not inline
├── audio_io.py    decode anything -> mono float32 @ SR; ffprobe metadata; .npy cache
├── features.py    chroma_cqt + per-dimension z-score + the ONE frame<->second conversion
├── matcher.py     sliding_correlation, find_peaks, match()
├── synth.py       Tier A clip generation (cut, stretch, noise) + the demo song
├── report.py      CSV, stdout table, score-curve plots
├── ingest.py      CLI: doctor / add / scan / list / probe / label
├── tier_a.py      CLI: the Tier A experiment and its gate
└── data/
    ├── reference/   full-length originals
    ├── clips/       Tier B phone recordings
    ├── inbox/       drop zone for `ingest scan`
    ├── synthetic/   generated clips (regenerable)
    └── cache/       decoded audio + stretched reference features
```

## Implementation notes

Things that are easy to get wrong here, and how this code handles them.

**Two timelines.** Per the spec, `match` time-stretches the *reference* to each candidate
rate and correlates the clip against it. The peak lands in the *stretched* timeline; a
point at original time `t` sits at `t / rate` after stretching, so the offset is multiplied
by `rate` on the way out. Every reported offset is in the original reference timeline —
the one you read off in Audacity. `--stretch clip` stretches the clip back to reference
speed instead, where no rescale is needed; it is much cheaper and moves the phase-vocoder
artifacts onto the clip, which is worth trying if 0.75x fails.

**Overlap normalization needs a floor.** Dividing correlation by overlap length stops
results clustering mid-reference, but without a minimum overlap a two-frame edge alignment
divides by two and outscores everything. Lags below `MIN_OVERLAP_FRAC` of the clip are
masked out.

**Feature-frame conversion lives in one function.** `features.frames_to_sec` is the only
place frames become seconds, so an error there shows up as a constant offset everywhere
rather than as an inconsistency between the plot and the table.

**`peak_ratio` compares within one rate curve** — winner over the best peak more than
`PEAK_EXCLUDE_SEC` away. Without the exclusion window, the runner-up is just the frame next
door and the ratio is always ~1.

**Reference features are cached.** Time-stretching a full song is tens of seconds and
dominates everything else; results are cached in `data/cache/` keyed on file mtime+size, so
re-runs and multi-clip runs pay it once.

**Watch out for self-similar test material.** The first version of the demo song cycled its
chord progression on a fixed formula and came out exactly periodic with a 72 s period —
three tied correlation peaks that looked like a matcher bug and were not one. The demo now
uses a seeded random chord order. Real songs have this property too, in weaker form: it is
the whole point of Tier B clip 6.
