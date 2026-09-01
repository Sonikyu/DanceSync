"""Pydantic models for API request/response bodies and persisted metadata."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class Candidate(BaseModel):
    """Mirrors `dancesync.types.Candidate` as a JSON-serializable model."""

    rate: float
    offset_sec: float
    score: float
    peak_ratio: float


class Reference(BaseModel):
    id: str
    filename: str
    duration_sec: float
    created_at: datetime


class AlignmentResult(BaseModel):
    top_candidates: list[Candidate]
    selected_index: int | None = None


class Clip(BaseModel):
    id: str
    reference_id: str
    filename: str
    alignment: AlignmentResult
    created_at: datetime


class SelectCandidateRequest(BaseModel):
    index: int
