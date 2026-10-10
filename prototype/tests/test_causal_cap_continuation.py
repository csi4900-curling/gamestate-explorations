from prototype.causal_cap_continuation import choose_next_cap


def component(x, y):
    return {"centroid_px_1080": [x, y], "area_px2": 120}


def test_chooses_component_from_past_motion_only():
    decision = choose_next_cap([10, 20], [0, 20], 1, [component(19, 21), component(60, 22)])
    assert decision["status"] == "unique_motion_gate_choice"
    assert decision["selected"] == component(19, 21)


def test_abstains_on_competing_caps_or_missing_cap():
    competing = choose_next_cap([10, 20], [0, 20], 1, [component(19, 21), component(22, 19)])
    assert competing["status"] == "competing_caps_inside_motion_gate"
    assert competing["selected"] is None
    missing = choose_next_cap([10, 20], [0, 20], 1, [component(200, 200)])
    assert missing["status"] == "no_cap_inside_motion_gate"


def test_abstains_on_unexpected_large_step_even_if_prediction_gate_allows_it():
    decision = choose_next_cap([10, 20], [0, 20], 1, [component(55, 25)])
    assert decision["status"] == "no_cap_inside_motion_gate"
