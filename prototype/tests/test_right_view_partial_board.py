"""Stable right-camera cap proposals require three source samples."""

from right_view_partial_board import stable_cap_candidates


def frame(t, points):
    return {"time_s": t, "cap_candidates": [
        {"colour": colour, "pixel": [x, y], "cap_area_px2": 20}
        for colour, x, y in points]}


def test_stable_cap_requires_three_nearby_same_colour_observations():
    frames = [frame(1, [("red", 400, 200), ("yellow", 500, 180)]),
              frame(6, [("red", 402, 201), ("yellow", 540, 180)]),
              frame(11, [("red", 401, 200), ("yellow", 500, 180)])]
    result = stable_cap_candidates(frames)
    assert len(result) == 1
    assert result[0]["colour"] == "red"
    assert result[0]["pixel_center"] == [401, 200]
    assert not result[0]["physical_stone_identity_verified"]


def test_missing_middle_sample_cannot_be_rescued_by_last_sample():
    frames = [frame(1, [("red", 400, 200)]), frame(6, []),
              frame(11, [("red", 400, 200)])]
    assert stable_cap_candidates(frames) == []
