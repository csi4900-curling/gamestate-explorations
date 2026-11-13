from prototype.right_full_match_temporal_inventory import candidate_left_ids, inventory


def event(id, colour, t):
    return {"id": id, "colour": colour, "crossing_time_s": t}


def proposal(id, colour, t, direction):
    return {
        "raw_track_id": id,
        "colour_claim": colour,
        "passage": {"time_s": t},
        "direction": direction,
        "observed_prefix_interval_s": [t - 1, t + 1],
    }


def test_direction_aware_candidates_reverse_temporal_order():
    left = [event("L1", "yellow", 10), event("L2", "yellow", 30)]
    assert candidate_left_ids(left, proposal("R1", "yellow", 18, "negative_y")) == ["L1"]
    assert candidate_left_ids(left, proposal("R2", "yellow", 18, "positive_y")) == ["L2"]


def test_inventory_keeps_unmatched_and_duplicate_candidates_for_review():
    left = [event("L1", "red", 10), event("L2", "yellow", 30)]
    right = [
        proposal("R1", "red", 15, "negative_y"),
        proposal("R2", "red", 16, "negative_y"),
        proposal("R3", "yellow", 5, "negative_y"),
    ]
    result = inventory(left, [("run", right)])
    assert result["status_counts"] == {
        "multiple_right_candidates_for_left_review": 2,
        "no_left_time_colour_candidate": 1,
    }
    assert result["left_events_without_any_right_time_colour_candidate"] == ["L2"]


def test_run_boundaries_prevent_cross_run_candidate_link():
    left = [event("L1", "red", 19)]
    right = [proposal("R1", "red", 21, "negative_y")]
    result = inventory(left, [("R02", right, (20, 40))])
    assert result["rows"][0]["temporal_status"] == "no_left_time_colour_candidate"
