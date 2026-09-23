"""Pydantic models for API request/response bodies and persisted metadata."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from dancesync.sync import Sound

# Which synced render: the take alone, or with the reference video beside it
# or above it.
Layout = Literal["take", "side-by-side", "stacked"]


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


class ManualAlignment(BaseModel):
    """An alignment the dancer set by hand, which overrides the matcher's
    without replacing it. `offset_sec` is in the ORIGINAL reference timeline,
    like a candidate's. No score or peak_ratio: they mean nothing here."""

    rate: float
    offset_sec: float


class AlignmentResult(BaseModel):
    """`ambiguous` and `failed` are decided once, at upload, against the
    matcher's `AMBIGUOUS_PEAK_RATIO` and `MIN_MATCH_SCORE`. The UI asks the
    user to pick a candidate when `ambiguous` is set, and says the take
    wasn't found in the song when `failed` is. `manual`, when set, wins over
    the chosen candidate everywhere (`effective_alignment`). Records saved
    before `failed` or `manual` existed load as not failed and not manual."""

    top_candidates: list[Candidate]
    ambiguous: bool
    failed: bool = False
    selected_index: int | None = None
    manual: ManualAlignment | None = None


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


def effective_alignment(alignment: AlignmentResult) -> ManualAlignment | Candidate:
    """What the take plays at: the dancer's manual alignment if they set one,
    else their pick of the candidates, else the matcher's best guess.
    `flow.effectiveAlignment` is the browser's copy of this rule."""
    if alignment.manual is not None:
        return alignment.manual
    index = alignment.selected_index
    return alignment.top_candidates[0 if index is None else index]


class RenderParams(BaseModel):
    """Everything a synced render depends on (invariant 7). Its cache id is
    built from every field, and the browser's `/synced` URL carries every
    field but `clip_id`, which is in the path. `RENDER_PARAM_FIELDS` in
    `web/src/api.js` lists them for the browser; a test fails if the two
    lists drift. Anything new that changes a render's picture or sound is a
    new field here."""

    clip_id: str
    reference_id: str
    rate: float
    offset_sec: float
    layout: Layout
    sound: Sound


def render_cache_id(params: RenderParams) -> str:
    """The render's filename stem: every field's value, in field order, so a
    new field changes it with no edit here. Floats keep full precision, since
    rounding could file two different renders under one name."""
    return "-".join(_cache_id_token(value) for value in params.model_dump().values())


def _cache_id_token(value: object) -> str:
    return repr(value) if isinstance(value, float) else str(value)
