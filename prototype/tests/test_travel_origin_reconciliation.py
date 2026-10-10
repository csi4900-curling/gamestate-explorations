import pytest

from travel_origin_reconciliation import classify_travel_predecessors


def fixtures():
    shots = [
        {"shot_id": "S1", "interval_s": [0.0, 10.0]},
        {"shot_id": "S2", "interval_s": [10.0, 20.0]},
    ]
    event = {
        "shot_id": "S1",
        "delivery_window_s": [0.0, 10.0],
        "colour": "red",
        "colour_status": "resolved",
        "counter_id": None,
    }
    travel = {
        "status": "unlocalized_travel_candidate",
        "counter_id": "B1",
        "colour": "yellow",
        "travel_shot_id": "S2",
        "observed_travel_window_s": [10.0, 18.0],
    }
    return shots, event, travel


def test_adjacent_colour_conflict_is_preserved_without_merge():
    shots, event, travel = fixtures()
    row = classify_travel_predecessors(shots, [event], [travel])[0]
    assert row["relation_status"] == "adjacent_visual_colour_conflict"
    assert row["possible_same_physical_throw"] is True
    assert row["merge_applied"] is False
    assert row["physical_identity_verified"] is False


def test_same_colour_and_counter_backed_predecessor_are_distinct():
    shots, event, travel = fixtures()
    event["colour"] = "yellow"
    row = classify_travel_predecessors(shots, [event], [travel])[0]
    assert row["relation_status"] == "adjacent_visual_same_colour"
    event["counter_id"] = "B0"
    row = classify_travel_predecessors(shots, [event], [travel])[0]
    assert row["relation_status"] == "adjacent_event_has_own_counter"
    assert row["possible_same_physical_throw"] is False


def test_missing_predecessor_is_explicit_and_bad_shot_rejected():
    shots, _, travel = fixtures()
    row = classify_travel_predecessors(shots, [], [travel])[0]
    assert row["relation_status"] == "no_adjacent_fused_event"
    assert row["preceding_shot_id"] == "S1"
    travel["travel_shot_id"] = "S99"
    with pytest.raises(ValueError, match="Unknown travel shot"):
        classify_travel_predecessors(shots, [], [travel])
