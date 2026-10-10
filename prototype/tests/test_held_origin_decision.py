"""Strong held or moving evidence can correct a weak gate colour."""

from held_origin_decision import combine_with_gate, held_motion_override


def evidence(red_hold=0, yellow_hold=0, red_motion=0, yellow_motion=0):
    return {
        "red": {"best_hold": {"duration_s": red_hold, "interval_s": [1, 2]}
                if red_hold else None,
                "best_motion": {"displacement_px": red_motion, "interval_s": [2, 3]}
                if red_motion else None},
        "yellow": {"best_hold": {"duration_s": yellow_hold, "interval_s": [1, 2]}
                   if yellow_hold else None,
                   "best_motion": {"displacement_px": yellow_motion,
                                   "interval_s": [2, 3]} if yellow_motion else None},
    }


def test_long_held_yellow_corrects_red_gate():
    result = combine_with_gate("red", evidence(yellow_hold=4.4, red_motion=37))
    assert result["colour"] == "yellow"
    assert result["route"] == "held_cap_overrode_gate"


def test_yellow_motion_wins_by_clear_margin():
    result = held_motion_override(evidence(red_motion=43, yellow_motion=85))
    assert result["colour"] == "yellow"


def test_near_tie_abstains_and_keeps_gate():
    result = combine_with_gate("red", evidence(red_motion=68, yellow_motion=69))
    assert result["colour"] == "red"
    assert result["route"] == "gate_unmodified"
