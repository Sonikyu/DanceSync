"""Tier A -- synthetic alignment test. Tests the code, not the world.

    python -m spike.tier_a                        # uses the only imported reference
    python -m spike.tier_a --ref my-song --start 90
    python -m spike.tier_a --sweep                # rate x SNR x position matrix
    python -m spike.tier_a --save-clips           # also write the clips as .wav

Gate: the matcher must recover the correct rate and land within ~50 ms of the
known cut position. A failure here is a bug -- indexing, normalization, or
frame/second conversion -- and the spec is explicit that you do not want to be
debugging it with real recordings in the mix.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import List, Optional

from spike import audio_io, ingest, report, synth
from spike.config import (
    HOP, MIN_OVERLAP_FRAC, PLOTS_DIR, RATES, RESULTS_DIR, SR,
    SYNTHETIC_DIR, ensure_dirs,
)
from spike.matcher import match, precompute_ref_features

TOLERANCE_SEC = 0.05          # the spec's "~50 ms"
RANK_TOLERANCE_SEC = 0.5      # how close a top-3 peak must be to count as correct


def resolve_reference(spec: Optional[str], demo: bool = False) -> Path:
    """Accept a path, an imported name, or nothing at all if there is exactly one."""
    if demo:
        path = SYNTHETIC_DIR / "demo-reference.wav"
        if not path.exists():
            synth.write_wav(path, synth.demo_reference(sr=SR), SR)
            print(f"  generated {path}")
        return path
    if spec:
        as_path = Path(spec).expanduser()
        if as_path.is_file():
            return as_path.resolve()
        entry = ingest.find_entry(spec, kind="reference")
        if entry:
            return ingest.resolve_path(entry)
        raise SystemExit(f"no reference named or located at {spec!r}. "
                         f"Import one:  python -m spike.ingest add <file> --kind reference")

    entries = ingest.load_manifest()["reference"]
    if len(entries) == 1:
        return ingest.resolve_path(entries[0])
    if not entries:
        raise SystemExit(
            "no reference imported yet.\n"
            "  python -m spike.ingest add /path/to/song.mp3 --kind reference"
        )
    names = ", ".join(e["name"] for e in entries)
    raise SystemExit(f"several references imported ({names}); pick one with --ref")


def build_cases(args, ref_duration: float) -> List[dict]:
    """One spec-exact case by default; a small matrix under --sweep."""
    dur = args.duration
    if args.sweep:
        # Two positions well inside the song, so nothing runs off either end.
        starts = [round(ref_duration * f) for f in (0.30, 0.60)]
        rates = [1.0, 0.75]
        snrs = [None, 20.0, 10.0]
    else:
        starts = [args.start if args.start is not None else round(ref_duration * 0.40)]
        rates = [args.rate]
        snrs = [None if args.snr is None else float(args.snr)]

    cases = []
    for start in starts:
        if start + dur > ref_duration:
            print(f"  ! skipping start={start}s: chunk runs past the end "
                  f"({ref_duration:.1f}s reference)", file=sys.stderr)
            continue
        for rate in rates:
            for snr in snrs:
                cases.append({"start": float(start), "rate": float(rate), "snr": snr})
    if not cases:
        raise SystemExit("no runnable cases -- reference too short for the requested duration")
    return cases


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    ensure_dirs()

    ref_path = resolve_reference(args.ref, demo=args.demo)
    print(f"reference: {ref_path.name}")
    ref_audio = audio_io.load_audio(ref_path, sr=SR)
    ref_duration = audio_io.duration_sec(ref_audio, SR)
    print(f"  {ref_duration:.1f}s @ {SR} Hz, hop={args.hop} "
          f"({args.hop / SR * 1000:.1f} ms/frame)")

    rates = tuple(args.rates) if args.rates else RATES
    cases = build_cases(args, ref_duration)
    print(f"  searching rates {rates}, stretching the {args.stretch}, "
          f"{len(cases)} case(s)\n")

    ref_features = None
    if args.stretch == "ref":
        t0 = time.perf_counter()
        ref_features = precompute_ref_features(
            ref_audio, rates=rates, sr=SR, hop=args.hop,
            cache_key=audio_io.file_key(ref_path, sr=SR, hop=args.hop, rates=rates),
        )
        print(f"  stretched reference features ready in {time.perf_counter() - t0:.1f}s "
              f"(cached in data/cache for re-runs)\n")

    rows = []
    for i, case in enumerate(cases, start=1):
        clip = synth.make_clip(
            ref_audio, start_sec=case["start"], duration_sec=args.duration,
            rate=case["rate"], snr_db=case["snr"], sr=SR, seed=args.seed,
        )
        if args.save_clips:
            synth.write_wav(SYNTHETIC_DIR / f"tier_a_{i:02d}_{clip.label}.wav", clip.audio, SR)

        t0 = time.perf_counter()
        result = match(
            clip.audio, ref_audio, rates=rates, sr=SR, hop=args.hop,
            stretch=args.stretch, min_overlap_frac=args.min_overlap,
            ref_features=ref_features,
        )
        elapsed = time.perf_counter() - t0

        error = result.offset_sec - clip.true_offset_sec
        rate_ok = abs(result.rate - clip.true_rate) < 1e-9
        passed = rate_ok and abs(error) <= args.tolerance
        rank = result.rank_of(clip.true_offset_sec, tol_sec=RANK_TOLERANCE_SEC)

        plot_path = PLOTS_DIR / f"tier_a_{i:02d}_{clip.label}.png"
        report.plot_scores(
            result, plot_path,
            title=f"Tier A #{i:02d}  {ref_path.name}  {clip.label}",
            true_offset_sec=clip.true_offset_sec,
        )

        rows.append({
            "case": i,
            "true_offset": clip.true_offset_sec,
            "pred_offset": result.offset_sec,
            "error_ms": error * 1000.0,
            "true_rate": clip.true_rate,
            "pred_rate": result.rate,
            "snr_db": clip.snr_db if clip.snr_db is not None else "clean",
            "peak_ratio": result.peak_ratio,
            "truth_rank": rank if rank else "-",
            "sec": elapsed,
            "pass": passed,
        })
        print(f"  #{i:02d} {clip.label:<26} "
              f"pred {result.rate:g}x @ {result.offset_sec:8.3f}s  "
              f"err {error * 1000:+8.1f} ms  ratio {result.peak_ratio:5.2f}  "
              f"{'PASS' if passed else 'FAIL'}")
        if not passed:
            print(f"       top peaks: {report.format_top_peaks(result)}")

    print()
    report.print_table(rows)

    csv_path = report.write_csv(rows, RESULTS_DIR / "tier_a.csv")
    print(f"\nresults: {csv_path}")
    print(f"plots:   {PLOTS_DIR}")

    n_pass = sum(1 for r in rows if r["pass"])
    if n_pass == len(rows):
        print(f"\nGATE PASSED  ({n_pass}/{len(rows)})  -- Tier A is clean, go film Tier B.")
        return 0

    print(f"\nGATE FAILED  ({n_pass}/{len(rows)} passed)")
    print("This is a bug in the code, not a finding about the world. Usual suspects:")
    print("  - frame <-> second conversion (features.frames_to_sec)")
    print("  - the stretched-timeline -> original-timeline rescale in matcher.match")
    print("  - z-scoring the wrong axis in features.normalize")
    print("  - overlap normalization / masking in matcher.sliding_correlation")
    print("Fix it before touching Tier B.")
    return 1


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="python -m spike.tier_a", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--ref", help="imported reference name, or a path to an audio file")
    p.add_argument("--demo", action="store_true",
                   help="use a generated fake song instead of a real reference "
                        "(smoke-tests the install; not a real Tier A result)")
    p.add_argument("--start", type=float,
                   help="cut position in seconds (default: 40%% into the song)")
    p.add_argument("--duration", type=float, default=30.0, help="clip length (default 30)")
    p.add_argument("--rate", type=float, default=0.75, help="playback rate to simulate")
    p.add_argument("--snr", type=float, default=10.0,
                   help="white-noise SNR in dB; pass --no-noise for a clean clip")
    p.add_argument("--no-noise", action="store_const", const=None, dest="snr")
    p.add_argument("--sweep", action="store_true",
                   help="run a rate x SNR x position matrix instead of one case")
    p.add_argument("--rates", type=float, nargs="+",
                   help=f"candidate rates to search (default {RATES})")
    p.add_argument("--stretch", choices=("ref", "clip"), default="ref",
                   help="which side to time-stretch (default: ref, as specified)")
    p.add_argument("--hop", type=int, default=HOP, help=f"feature hop length (default {HOP})")
    p.add_argument("--min-overlap", type=float, default=MIN_OVERLAP_FRAC,
                   help="minimum clip overlap fraction for a lag to be scored")
    p.add_argument("--tolerance", type=float, default=TOLERANCE_SEC,
                   help=f"pass tolerance in seconds (default {TOLERANCE_SEC})")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--save-clips", action="store_true",
                   help="write generated clips to data/synthetic as .wav")
    return p


if __name__ == "__main__":
    raise SystemExit(main())
