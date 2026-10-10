"""Early right-view line timings stay tied to observed motion brackets."""

from right_view_entry_triage import crossing, triage_tracks


def point(t, x, y, area=25, width=10, height=6):
    return {"time_s": t, "pixel": [x, y], "bbox": [x - 5, y - 3, width, height],
            "cap_area_px2": area}


def test_crossing_is_interpolated_only_between_observed_points():
    row = crossing([point(10, 500, 270), point(11, 490, 230)], 250)
    assert row == {"time_s": 10.5, "x_px": 495.0, "bracket_s": [10, 11]}


def test_entry_prefix_stops_at_first_confirming_point():
    tracks = [{"track_id": "R1", "colour": "red",
               "points": [point(10, 500, 300), point(11, 498, 260),
                          point(12, 496, 240), point(14, 492, 210),
                          point(100, 300, 150)]}]
    proposal = triage_tracks(tracks)[0]
    assert proposal["entry_crossing"]["bracket_s"] == [11, 12]
    assert proposal["confirmation_time_s"] == 14
    assert len(proposal["observed_prefix_points"]) == 4
    assert proposal["release_time_s"] is None


def test_small_vertical_player_patch_does_not_enter_review_tier():
    tracks = [{"track_id": "P", "colour": "red",
               "points": [point(10, 500, 300, area=5, width=4, height=6),
                          point(14, 490, 210)]}]
    assert triage_tracks(tracks) == []
