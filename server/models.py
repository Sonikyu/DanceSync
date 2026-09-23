"""Pydantic models for API request/response bodies and persisted metadata."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

# Which synced render: the take alone, or side by side with the reference video.
Layout = Literal["take", "side-by-side"]


class Candidate(BaseModel):
    """Mirrors `dancesync.types.Candidate` as a JSON-serializable model.

    `peak_ratio` is None when the winner has no competing peak at all. The
    matcher reports that as infinity, which JSON can't carry.
    """

    rate: float
    offset_sec: float
    score: float
    peak_ratio: float | None


class Reference(BaseModel):
    id: str
    filename: str
    duration_sec: float
    created_at: datetime


class AlignmentResult(BaseModel):
    """`ambiguous` and `failed` are decided once, at upload, against the
    matcher's `AMBIGUOUS_PEAK_RATIO` and `MIN_MATCH_SCORE`. The UI asks the
    user to pick a candidate when `ambiguous` is set, and says the take
    wasn't found in the song when `failed` is. Records saved before `failed`
    existed load as not failed."""

    top_candidates: list[Candidate]
    ambiguous: bool
    failed: bool = False
    selected_index: int | None = None


class Clip(BaseModel):
    id: str
    reference_id: str
    filename: str
    alignment: AlignmentResult
    created_at: datetime


class SelectCandidateRequest(BaseModel):
    index: int


class SignInRequest(BaseModel):
    passphrase: str


class SessionStatus(BaseModel):
    signed_in: bool
