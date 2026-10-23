"""The edit filter strings, checked as strings: no ffmpeg runs here.
`test_sync.py` renders them for real."""

from __future__ import annotations

import pytest

from dancesync.framing import crop_filter, framing_chain, framing_filters, trim_chain
from dancesync.types import Crop, Framing, Trim

CROP = Crop(x=0.25, y=0.1, w=0.5, h=0.8)
CROP_FILTER = "crop=trunc(iw*0.500000/2)*2:trunc(ih*0.800000/2)*2:iw*0.250000:ih*0.100000"


def test_unedited_has_no_filters():
    assert framing_filters(Framing()) == []
    assert framing_chain(Framing()) == ""


@pytest.mark.parametrize(
    ("rotate", "filters"),
    [(90, ["transpose=1"]), (180, ["hflip", "vflip"]), (270, ["transpose=2"])],
)
def test_rotate_turns_clockwise(rotate, filters):
    assert framing_filters(Framing(rotate=rotate)) == filters


def test_crop_rounds_width_and_height_down_to_even():
    assert crop_filter(CROP) == CROP_FILTER


def test_mirror_flips_horizontally():
    assert framing_filters(Framing(mirror=True)) == ["hflip"]


def test_combined_edits_run_rotate_crop_mirror():
    framing = Framing(rotate=90, crop=CROP, mirror=True)

    assert framing_filters(framing) == ["transpose=1", CROP_FILTER, "hflip"]
    assert framing_chain(framing) == f"transpose=1,{CROP_FILTER},hflip,"


def test_crop_then_mirror_without_rotation():
    assert framing_filters(Framing(crop=CROP, mirror=True)) == [CROP_FILTER, "hflip"]


def test_trim_keeps_the_stretch_and_restarts_the_clock():
    assert trim_chain(Trim(1.5, 9.25), "") == "trim=start=1.500000:end=9.250000,setpts=PTS-STARTPTS,"
    assert trim_chain(Trim(1.5, 9.25), "a") == "atrim=start=1.500000:end=9.250000,asetpts=PTS-STARTPTS,"


def test_no_trim_is_no_filter():
    assert trim_chain(None, "a") == ""
