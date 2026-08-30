"""Result tables and score-curve plots -- the spike's actual deliverable."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence

import numpy as np

from spike.matcher import MatchResult


def write_csv(rows: Sequence[Dict], path: Path, fieldnames: Optional[List[str]] = None) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("")
        return path
    fieldnames = fieldnames or list(rows[0].keys())
    with path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return path


def print_table(rows: Sequence[Dict], columns: Optional[Sequence[str]] = None) -> None:
    if not rows:
        print("(no rows)")
        return
    columns = list(columns or rows[0].keys())
    widths = {
        c: max(len(str(c)), max(len(_fmt(r.get(c))) for r in rows))
        for c in columns
    }
    header = "  ".join(str(c).ljust(widths[c]) for c in columns)
    print(header)
    print("  ".join("-" * widths[c] for c in columns))
    for r in rows:
        print("  ".join(_fmt(r.get(c)).ljust(widths[c]) for c in columns))


def _fmt(v) -> str:
    if v is None:
        return "-"
    if isinstance(v, float):
        return f"{v:.3f}"
    if isinstance(v, bool):
        return "PASS" if v else "FAIL"
    return str(v)


def plot_scores(
    result: MatchResult,
    out_path: Path,
    title: str = "",
    true_offset_sec: Optional[float] = None,
) -> Path:
    """One panel per candidate rate, x-axis in original-reference seconds."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    curves = result.per_rate
    fig, axes = plt.subplots(len(curves), 1, figsize=(11, 2.4 * len(curves)),
                             sharex=True, squeeze=False)
    axes = axes[:, 0]

    for ax, rs in zip(axes, curves):
        finite = np.isfinite(rs.scores)
        ax.plot(rs.offsets_sec[finite], rs.scores[finite], lw=0.8)
        won = rs.rate == result.rate
        ax.set_ylabel(f"rate {rs.rate:g}" + ("  *" if won else ""),
                      fontweight="bold" if won else "normal")

        if won:
            ax.axvline(result.offset_sec, color="tab:red", lw=1.2,
                       label=f"predicted {result.offset_sec:.2f}s")
        if true_offset_sec is not None:
            ax.axvline(true_offset_sec, color="tab:green", ls="--", lw=1.2,
                       label=f"truth {true_offset_sec:.2f}s")
        if ax.get_legend_handles_labels()[0]:
            ax.legend(loc="upper right", fontsize=8)

    axes[-1].set_xlabel("offset into reference (s)")
    head = title or "score curves"
    fig.suptitle(f"{head}\nbest: rate={result.rate:g}  offset={result.offset_sec:.3f}s  "
                 f"peak_ratio={result.peak_ratio:.2f}", fontsize=10)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(out_path, dpi=120)
    plt.close(fig)
    return out_path


def format_top_peaks(result: MatchResult) -> str:
    return " | ".join(
        f"{p.rate:g}x@{p.offset_sec:.2f}s({p.score:.2f})" for p in result.top_peaks
    )
