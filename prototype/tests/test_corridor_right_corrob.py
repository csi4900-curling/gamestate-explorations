from prototype.corridor_right_corrob import corroborate_left_proposals


def test_respects_both_direction_orders_and_shared_right_ambiguity():
    left = [
        {"id": "L1", "colour": "yellow", "view_motion": "positive_y",
         "crossing_time_s": 100},
        {"id": "L2", "colour": "red", "view_motion": "negative_y",
         "crossing_time_s": 200},
        {"id": "L3", "colour": "yellow", "view_motion": "positive_y",
         "crossing_time_s": 101},
    ]
    right = [
        {"proposal_id": "R1", "colour_claim": "yellow", "direction": "positive_y",
         "passage_time_s": 95},
        {"proposal_id": "R2", "colour_claim": "red", "direction": "negative_y",
         "passage_time_s": 205},
        {"proposal_id": "R3", "colour_claim": "red", "direction": "positive_y",
         "passage_time_s": 202},
    ]
    a, b, c = corroborate_left_proposals(left, right)
    assert a["shared_right_candidate_ids"] == ["R1"]
    assert c["shared_right_candidate_ids"] == ["R1"]
    assert a["corroboration_tier"] == "ambiguous_right_candidates"
    assert b["unique_right_candidate_ids"] == ["R2"]
    assert b["corroboration_tier"] == "unique_right_time_colour_direction_candidate"
