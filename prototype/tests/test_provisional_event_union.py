from copy import deepcopy

import pytest

from provisional_event_union import combine_event_evidence


def baseline(counter_id="B1"):
    return {"shot_id": "S1", "delivery_window_s": [0.0, 10.0],
            "counter_id": counter_id, "colour": "yellow",
            "colour_status": "resolved", "evidence_sources": ["visual_origin"]}


def travel(counter_id="B1"):
    return {"status": "unlocalized_travel_candidate",
            "counter_id": counter_id, "colour": "yellow", "travel_shot_id": "S2",
            "release_window_s": [0.0, 10.0],
            "observed_travel_window_s": [10.0, 20.0],
            "candidate_shots": [{"channel_support": ["cap", "learned"]}]}


def relation(counter_id="B1", possible=False):
    return {"counter_id": counter_id, "travel_shot_id": "S2",
            "relation_status": ("adjacent_visual_colour_conflict" if possible else
                                "adjacent_event_has_own_counter"),
            "possible_same_physical_throw": possible,
            "preceding_fused_event": {"shot_id": "S1"} if possible else None}


def held(counter_id="B1"):
    return {"counter_id": counter_id, "shot_id": "S3",
            "delivery_window_s": [0.0, 10.0], "held_interval_s": [5.0, 7.0],
            "release_cue_s": 7.2, "below_ice_fraction": 0.8,
            "colour": "yellow"}


def test_travel_and_held_cues_attach_once_to_counter_linked_event():
    result = combine_event_evidence([baseline()], [travel()], [relation()], [held()])
    assert len(result["events"]) == 1
    row = result["events"][0]
    assert row["source_shot_ids"] == ["S1", "S2", "S3"]
    assert row["attached_travel_evidence"] is not None
    assert row["attached_held_evidence"] is not None
    assert row["physical_stone_identity_verified"] is False
    assert row["simulation_ready"] is False


def test_possible_visual_duplicate_abstains_from_new_event():
    result = combine_event_evidence([baseline(None)], [travel()],
                                    [relation(possible=True)], [])
    assert len(result["events"]) == 1
    assert result["unassigned_travel_evidence"][0]["counter_id"] == "B1"


def test_residual_travel_and_held_only_create_distinct_provisional_events():
    result = combine_event_evidence([], [travel()], [relation()], [held("B2")])
    assert {row["event_id"] for row in result["events"]} == {
        "TRAVEL-B1", "HELD-B2"}
    assert all(row["simulation_ready"] is False for row in result["events"])


def test_duplicate_linked_counter_and_colour_mismatch_rejected():
    first = baseline()
    second = deepcopy(first)
    second["shot_id"] = "S4"
    with pytest.raises(ValueError, match="Duplicate linked counter"):
        combine_event_evidence([first, second], [], [], [])
    contradictory = held()
    contradictory["colour"] = "red"
    with pytest.raises(ValueError, match="contradicts resolved event colour"):
        combine_event_evidence([first], [], [], [contradictory])
