import pytest

from partial_board_transition import compare_partial_boards


def stone(colour, x, y):
    return {"colour": colour, "canonical_lateral_house_radii": x,
            "longitudinal_house_radii": y}


def board(shot, time_s, stones):
    return {"shot_id": shot, "counter_anchor_s": time_s,
            "stable_partial_board": stones}


def test_retention_and_changed_visible_stones_are_distinct():
    before = board("S12", 100, [stone("red", 0.8, -0.4),
                                 stone("yellow", -0.8, 0.5)])
    after = board("S13", 150, [stone("yellow", -0.79, 0.51),
                                stone("yellow", 0.8, -0.5)])
    result = compare_partial_boards(before, after)
    assert [(x["before_local_id"], x["after_local_id"])
            for x in result["locally_retained"]] == [("V02", "V01")]
    assert result["no_longer_observed"] == ["V01"]
    assert result["newly_observed"] == ["V02"]
    assert result["physical_transition_verified"] is False


def test_competing_nearby_stones_abstain_from_identity():
    before = board("S12", 100, [stone("yellow", 0, 0)])
    after = board("S13", 150, [stone("yellow", 0.02, 0),
                                stone("yellow", -0.02, 0)])
    result = compare_partial_boards(before, after)
    assert result["locally_retained"] == []
    assert result["unresolved_before"] == ["V01"]
    assert result["unresolved_after"] == ["V01", "V02"]
    assert result["newly_observed"] == []


def test_counter_order_must_advance():
    with pytest.raises(ValueError, match="advance"):
        compare_partial_boards(board("A", 100, []), board("B", 100, []))
