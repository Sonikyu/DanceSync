"""Invariant 7, enforced: every input to a render names its cache file on the
server and appears in the browser's /synced URL. Adding a field to
`RenderParams` without adding it to the browser's list fails here."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from server.models import RenderParams, render_cache_id

API_JS = Path(__file__).resolve().parent.parent / "web" / "src" / "api.js"

PARAMS = RenderParams(
    clip_id="clip", reference_id="ref", rate=0.75, offset_sec=12.25, layout="take", sound="song"
)

# One different value per field, to prove each one reaches the cache id.
CHANGED = {
    "clip_id": "other-clip",
    "reference_id": "other-ref",
    "rate": 0.5,
    "offset_sec": 12.2501,
    "layout": "side-by-side",
    "sound": "room",
}


def _browser_fields() -> list[str]:
    source = API_JS.read_text()
    listed = re.search(r"export const RENDER_PARAM_FIELDS = \[([^\]]*)\]", source)
    assert listed, "RENDER_PARAM_FIELDS not found in web/src/api.js"
    return re.findall(r'"(\w+)"', listed.group(1))


def test_browser_url_carries_every_render_param():
    # clip_id is the URL's path; everything else goes in the query.
    assert sorted(_browser_fields()) == sorted(set(RenderParams.model_fields) - {"clip_id"})


def test_every_field_has_a_changed_value_here():
    assert set(CHANGED) == set(RenderParams.model_fields)


@pytest.mark.parametrize("field", sorted(CHANGED))
def test_every_field_changes_the_cache_id(field):
    changed = PARAMS.model_copy(update={field: CHANGED[field]})

    assert render_cache_id(changed) != render_cache_id(PARAMS)


def test_cache_id_reads_like_the_inputs():
    assert render_cache_id(PARAMS) == "clip-ref-0.75-12.25-take-song"
