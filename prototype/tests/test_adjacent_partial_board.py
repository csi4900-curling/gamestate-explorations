"""Meaningful guardrails for partial board comparisons."""

from adjacent_partial_board import compare_adjacent_rows, compare_partial_boards


def stone(name, colour, x, y):
    return {"local_observation_id": name, "colour": colour,
            "view_local_ground_position_m": [x, y]}


def row(name, t, view, stones):
    return {"candidate_id": name, "crossing_time_s": t,
            "receiving_view": view,
            "board": {"status": "partial_stable_view_local_board",
                      "stones": stones}}


def test_crowded_nearby_observations_remain_unresolved():
    result = compare_partial_boards([stone("old", "red", 0, 0)],
                                    [stone("a", "red", 0.05, 0),
                                     stone("b", "red", -0.05, 0)])
    assert not result["matched_observations"]
    assert result["ambiguous_before_observations"] == ["old"]
    assert result["ambiguous_after_observations"] == ["a", "b"]


def test_intervening_candidate_blocks_apparent_board_transition():
    a = row("S01", 10, "right", [stone("a", "yellow", 0, 0)])
    b = row("S03", 30, "right", [stone("b", "yellow", 0.02, 0)])
    result = compare_adjacent_rows(a, b, [{"id": "S02", "crossing_time_s": 20}])
    assert result["status"] == "abstain_intervening_passage_candidate"
    assert "matched_observations" not in result


def test_view_change_blocks_coordinate_comparison():
    a = row("S01", 10, "left", [stone("a", "yellow", 0, 0)])
    b = row("S02", 20, "right", [stone("b", "yellow", 0, 0)])
    assert compare_adjacent_rows(a, b, [])["status"] == "abstain_camera_change"
