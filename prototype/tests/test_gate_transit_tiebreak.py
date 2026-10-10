from gate_transit_tiebreak import tiebreak_competing_transits


def track(displacement, score, points=5, ratio=1.01):
    return {
        "point_count": points,
        "displacement_px": displacement,
        "median_patch_score": score,
        "path_ratio": ratio,
        "interval_s": [10.0, 10.8],
    }


def test_clearer_yellow_transit_breaks_ambiguous_gate_tie():
    decision = {
        "colour": None,
        "colour_route": "ambiguous_competing_transits",
        "side": "left",
        "early_gate_anchor_s": None,
    }
    gate = {"left": {"transits": {"red": [track(38, 0.17)], "yellow": [track(74, 0.75)]}}}
    result = tiebreak_competing_transits(decision, gate)
    assert result["colour"] == "yellow"
    assert result["early_gate_anchor_s"] == 10.0


def test_weak_or_unreliable_transit_keeps_abstention():
    decision = {
        "colour": None,
        "colour_route": "ambiguous_competing_transits",
        "side": "left",
        "early_gate_anchor_s": None,
    }
    for yellow in (track(55, 0.8), track(80, 0.3), track(80, 0.8, ratio=1.4)):
        gate = {"left": {"transits": {"red": [track(38, 0.17)], "yellow": [yellow]}}}
        assert tiebreak_competing_transits(decision, gate) == decision


def test_existing_colour_decision_is_unchanged():
    decision = {
        "colour": "red",
        "colour_route": "coherent_early_gate_transit",
        "side": "left",
        "early_gate_anchor_s": 9.0,
    }
    assert tiebreak_competing_transits(decision, {}) == decision
