"""Import and track reference audio and test recordings.

    python -m spike.ingest doctor
    python -m spike.ingest add ~/Desktop/song.mp3 --kind reference
    python -m spike.ingest add ~/Desktop/IMG_4821.MOV --kind clip --ref song --rate 0.75 \
        --condition "Room A, hard surfaces"
    python -m spike.ingest scan --kind clip          # sweep everything in data/inbox
    python -m spike.ingest label clip-03 --truth 92.41
    python -m spike.ingest list

Video files are accepted purely as containers -- only their audio track is ever
decoded, and it is decoded lazily, at match time.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from spike import audio_io
from spike.config import (
    CLIPS_DIR, INBOX_DIR, MANIFEST, REFERENCE_DIR, ensure_dirs,
)

KINDS = ("reference", "clip")


# --- manifest -------------------------------------------------------------

def load_manifest() -> Dict[str, List[Dict]]:
    if MANIFEST.exists():
        data = json.loads(MANIFEST.read_text())
    else:
        data = {}
    return {kind: data.get(kind, []) for kind in KINDS}


def save_manifest(manifest: Dict[str, List[Dict]]) -> None:
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n")


def dir_for(kind: str) -> Path:
    return REFERENCE_DIR if kind == "reference" else CLIPS_DIR


def find_entry(name_or_file: str, kind: Optional[str] = None) -> Optional[Dict]:
    """Look an item up by its short name, its filename, or its stem."""
    manifest = load_manifest()
    kinds = [kind] if kind else list(KINDS)
    needle = name_or_file.lower()
    for k in kinds:
        for entry in manifest[k]:
            candidates = {entry["name"].lower(), entry["filename"].lower(),
                          Path(entry["filename"]).stem.lower()}
            if needle in candidates:
                return entry
    return None


def resolve_path(entry: Dict) -> Path:
    return dir_for(entry["kind"]) / entry["filename"]


# --- import ---------------------------------------------------------------

def slugify(stem: str) -> str:
    s = re.sub(r"[^\w\s.-]", "", stem, flags=re.UNICODE).strip().lower()
    s = re.sub(r"[\s_]+", "-", s)
    s = re.sub(r"-{2,}", "-", s).strip("-.")
    return s or "item"


def unique_destination(dest_dir: Path, filename: str) -> Path:
    dest = dest_dir / filename
    if not dest.exists():
        return dest
    stem, suffix = Path(filename).stem, Path(filename).suffix
    for i in range(2, 1000):
        candidate = dest_dir / f"{stem}-{i}{suffix}"
        if not candidate.exists():
            return candidate
    raise RuntimeError(f"cannot find a free filename for {filename}")


def import_file(
    src: Path,
    kind: str,
    name: Optional[str] = None,
    move: bool = False,
    **fields,
) -> Dict:
    src = Path(src).expanduser().resolve()
    if not src.is_file():
        raise FileNotFoundError(src)
    if not audio_io.is_supported(src):
        raise ValueError(
            f"{src.name}: unsupported extension '{src.suffix}'. Supported: "
            + ", ".join(sorted(audio_io.SUPPORTED_EXTS))
        )

    ensure_dirs()
    dest_dir = dir_for(kind)
    filename = slugify(src.stem) + src.suffix.lower()
    dest = unique_destination(dest_dir, filename)

    if move:
        shutil.move(str(src), str(dest))
    else:
        shutil.copy2(src, dest)

    info = audio_io.probe(dest)
    entry = {
        "name": name or dest.stem,
        "kind": kind,
        "filename": dest.name,
        "source": str(src),
        "added": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "duration_sec": round(info.duration_sec, 3) if info.duration_sec else None,
        "sample_rate": info.sample_rate,
        "channels": info.channels,
        "codec": info.codec,
        "has_video": info.has_video,
    }
    entry.update({k: v for k, v in fields.items() if v is not None})

    manifest = load_manifest()
    manifest[kind] = [e for e in manifest[kind] if e["filename"] != dest.name]
    manifest[kind].append(entry)
    save_manifest(manifest)
    return entry


# --- commands -------------------------------------------------------------

def cmd_add(args) -> int:
    failures = 0
    for raw in args.paths:
        try:
            entry = import_file(
                Path(raw), kind=args.kind, name=args.name, move=args.move,
                ref=args.ref, rate=args.rate, condition=args.condition,
                true_offset_sec=args.truth, notes=args.notes,
            )
        except Exception as exc:
            print(f"  skip {raw}: {exc}", file=sys.stderr)
            failures += 1
            continue
        info = audio_io.probe(resolve_path(entry))
        print(f"  {args.kind:<9} {entry['filename']:<38} {info.summary()}")
        if audio_io.needs_ffmpeg(resolve_path(entry)) and not audio_io.have_ffmpeg():
            print("    ! ffmpeg missing -- this file cannot be decoded yet "
                  "(brew install ffmpeg)", file=sys.stderr)
    return 1 if failures else 0


def cmd_scan(args) -> int:
    ensure_dirs()
    candidates = sorted(p for p in INBOX_DIR.iterdir()
                        if p.is_file() and not p.name.startswith("."))
    if not candidates:
        print(f"inbox is empty: {INBOX_DIR}")
        return 0

    usable = [p for p in candidates if audio_io.is_supported(p)]
    for p in candidates:
        if p not in usable:
            print(f"  skip {p.name}: unsupported extension", file=sys.stderr)

    args.paths = [str(p) for p in usable]
    args.name = None
    args.move = not args.copy
    return cmd_add(args)


def cmd_list(args) -> int:
    manifest = load_manifest()
    for kind in KINDS:
        entries = manifest[kind]
        print(f"\n{kind.upper()}  ({len(entries)})  {dir_for(kind)}")
        if not entries:
            print("  (none)")
            continue
        for e in entries:
            path = resolve_path(e)
            mark = " " if path.exists() else "!"
            dur = f"{e['duration_sec']:.1f}s" if e.get("duration_sec") else "?"
            bits = [f"{mark} {e['name']:<24} {dur:>8}  {e.get('codec') or '?'}"]
            if e.get("rate") is not None:
                bits.append(f"rate={e['rate']:g}")
            if e.get("true_offset_sec") is not None:
                bits.append(f"truth={e['true_offset_sec']:.2f}s")
            if e.get("ref"):
                bits.append(f"ref={e['ref']}")
            if e.get("condition"):
                bits.append(f"[{e['condition']}]")
            print("  " + "  ".join(bits))
            if not path.exists():
                print(f"    ! file missing on disk: {path}", file=sys.stderr)
    print()
    return 0


def cmd_probe(args) -> int:
    for raw in args.paths:
        entry = find_entry(raw)
        path = resolve_path(entry) if entry else Path(raw).expanduser()
        if not path.exists():
            print(f"  {raw}: not found", file=sys.stderr)
            continue
        print(f"  {path.name:<38} {audio_io.probe(path).summary()}")
    return 0


def cmd_label(args) -> int:
    manifest = load_manifest()
    for kind in KINDS:
        for entry in manifest[kind]:
            if args.name.lower() in {entry["name"].lower(),
                                     Path(entry["filename"]).stem.lower()}:
                for field, value in (("true_offset_sec", args.truth),
                                     ("rate", args.rate),
                                     ("condition", args.condition),
                                     ("ref", args.ref),
                                     ("notes", args.notes)):
                    if value is not None:
                        entry[field] = value
                save_manifest(manifest)
                print(f"  updated {entry['name']}: "
                      + ", ".join(f"{k}={entry[k]}" for k in
                                  ("rate", "true_offset_sec", "ref", "condition")
                                  if entry.get(k) is not None))
                return 0
    print(f"no item named {args.name!r} -- run `list` to see what is imported",
          file=sys.stderr)
    return 1


def cmd_doctor(args) -> int:
    ensure_dirs()
    ok = True

    print("dependencies")
    for mod in ("numpy", "librosa", "soundfile", "matplotlib"):
        try:
            __import__(mod)
            print(f"  ok    {mod}")
        except ImportError:
            print(f"  MISS  {mod}")
            ok = False

    print("\nexternal tools")
    if audio_io.have_ffmpeg():
        print("  ok    ffmpeg")
    else:
        print("  MISS  ffmpeg  -> brew install ffmpeg")
        print("        needed for .mov / .mp4 / .m4a / .mp3; .wav works without it")
        ok = False

    print("\nfolders")
    for d in (REFERENCE_DIR, CLIPS_DIR, INBOX_DIR):
        n = len([p for p in d.iterdir() if p.is_file() and not p.name.startswith(".")])
        print(f"  {d.relative_to(MANIFEST.parent.parent)}: {n} file(s)")

    if not ok:
        print("\nfix the MISS lines above, then re-run doctor.")
    return 0 if ok else 1


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="python -m spike.ingest", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="command", required=True)

    def add_meta(sp):
        sp.add_argument("--ref", help="name of the reference this clip belongs to")
        sp.add_argument("--rate", type=float, help="playback rate used when filming (e.g. 0.75)")
        sp.add_argument("--condition", help="free text, e.g. 'Room B, TV audible'")
        sp.add_argument("--truth", type=float, dest="truth",
                        help="ground-truth offset into the reference, in seconds")
        sp.add_argument("--notes")

    sp = sub.add_parser("add", help="copy files into data/reference or data/clips")
    sp.add_argument("paths", nargs="+")
    sp.add_argument("--kind", choices=KINDS, required=True)
    sp.add_argument("--name", help="short name (defaults to the sanitized filename)")
    sp.add_argument("--move", action="store_true", help="move instead of copy")
    add_meta(sp)
    sp.set_defaults(func=cmd_add)

    sp = sub.add_parser("scan", help="import everything sitting in data/inbox")
    sp.add_argument("--kind", choices=KINDS, required=True)
    sp.add_argument("--copy", action="store_true",
                    help="copy out of the inbox instead of moving")
    add_meta(sp)
    sp.set_defaults(func=cmd_scan)

    sp = sub.add_parser("list", help="show everything imported")
    sp.set_defaults(func=cmd_list)

    sp = sub.add_parser("probe", help="show format details for a file or imported name")
    sp.add_argument("paths", nargs="+")
    sp.set_defaults(func=cmd_probe)

    sp = sub.add_parser("label", help="attach ground truth / metadata to an imported item")
    sp.add_argument("name")
    add_meta(sp)
    sp.set_defaults(func=cmd_label)

    sp = sub.add_parser("doctor", help="check dependencies, ffmpeg, and folders")
    sp.set_defaults(func=cmd_doctor)
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    ensure_dirs()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
