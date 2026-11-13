"""Line-free review proposals must preserve existing entries and span semantics."""

import pytest

from right_view_span_fallback import span_fallback


def track(track_id="R1", y0=218, y1=150):
    return {
        "track_id": track_id,
        "colour": "yellow",
        "points": [
            {"time_s": 1.0, "pixel": [430, y0], "bbox": [422, y0 - 4, 16, 8], "cap_area_px2": 60},
            {"time_s": 4.0, "pixel": [424, y1], "bbox": [416, y1 - 4, 16, 8], "cap_area_px2": 55},
        ],
    }


def test_track_starting_beyond_entry_line_gets_observed_span_time():
    rows = span_fallback([track()], [])
    assert len(rows) == 1
    assert rows[0]["passage"]["time_s"] == 2.324
    assert rows[0]["passage"]["pixel"] == [427.35, 188.0]
    assert rows[0]["passage_kind"].endswith("not_fixed_line")


def test_existing_entry_not_duplicated_and_short_motion_not_added():
    assert span_fallback([track()], ["R1"]) == []
    assert span_fallback([track(y1=180)], []) == []


def test_duplicate_track_ids_rejected():
    with pytest.raises(ValueError, match="Duplicate raw track"):
        span_fallback([track(), track()], [])
    with pytest.raises(ValueError, match="Duplicate existing"):
        span_fallback([track()], ["R1", "R1"])
