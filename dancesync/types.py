"""Result types shared across the matcher and its callers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class Candidate:
    """One candidate alignment: a rate and an offset in the original reference timeline."""

    rate: float
    offset_sec: float
    score: float
    peak_ratio: float


@dataclass(frozen=True)
class MatchResult:
    """The outcome of aligning a clip against a reference track.

    `top_candidates` is ordered best-first and always non-empty; `rate`,
    `offset_sec`, `score`, and `peak_ratio` mirror `top_candidates[0]` for
    callers that only want the winner. The UI's ambiguity fallback (showing
    top-3 thumbnails when `peak_ratio` is low) reads `top_candidates` directly.
    """

    top_candidates: tuple[Candidate, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.top_candidates:
            raise ValueError("MatchResult requires at least one candidate")

    @property
    def rate(self) -> float:
        return self.top_candidates[0].rate

    @property
    def offset_sec(self) -> float:
        return self.top_candidates[0].offset_sec

    @property
    def score(self) -> float:
        return self.top_candidates[0].score

    @property
    def peak_ratio(self) -> float:
        return self.top_candidates[0].peak_ratio

    def rank_of(self, true_offset_sec: float, tol_sec: float = 0.5) -> Optional[int]:
        """1-based rank of the first candidate within `tol_sec` of the truth, else None."""
        for i, c in enumerate(self.top_candidates, start=1):
            if abs(c.offset_sec - true_offset_sec) <= tol_sec:
                return i
        return None
