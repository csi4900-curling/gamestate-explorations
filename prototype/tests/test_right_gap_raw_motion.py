from prototype.right_gap_raw_motion import latest_short_motion, rescue_left_only


def point(t, y, area=10):
    return {"time_s": t, "pixel": [100, y], "bbox": [95, y - 4, 10, 8], "cap_area_px2": area}


def test_left_only_gap_can_use_short_raw_motion_below_strict_threshold():
    track = {
        "track_id": "A1",
        "colour": "red",
        "points": [point(10, 100), point(11, 118), point(12, 136)],
    }
    event = {"id": "L1", "colour": "red", "crossing_time_s": 18}
    candidate = latest_short_motion(track, event)
    assert candidate is not None
    assert candidate["left_event_id_for_targeted_search"] == "L1"
    assert candidate["observed_prefix_interval_s"] == [10, 12]


def test_targeted_rescue_preserves_no_candidate_and_wrong_colour():
    event = {"id": "L1", "colour": "yellow", "crossing_time_s": 18}
    track = {
        "track_id": "A1",
        "colour": "red",
        "points": [point(10, 100), point(11, 118), point(12, 136)],
    }
    rows = rescue_left_only([event], {"R1": [track]}, supported_runs={"R1": (0, 30)})
    assert rows[0]["candidate_count"] == 0
