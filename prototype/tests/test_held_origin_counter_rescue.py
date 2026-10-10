from copy import deepcopy

import pytest

from held_origin_counter_rescue import propose_held_origin_rescues


def sample():
    fused = {"events": [], "unassociated_counter_events": [
        {"counter_id": "B1", "colour": "red", "counter_update_s": 30.0}]}
    held = {"shot_id": "S1", "origin_interval_s": [10.0, 21.0],
            "unique_passage_colour": "red", "accepted_passages": [{
                "colour": "red", "held_interval_s": [17.0, 19.0],
                "release_cue_s": 19.2, "below_ice_fraction": 0.8}]}
    return fused, held


def test_unique_source_cues_propose_an_uncertain_event():
    fused, held = sample()
    result = propose_held_origin_rescues(fused, [held])
    assert len(result["proposals"]) == 1
    proposal = result["proposals"][0]
    assert (proposal["shot_id"], proposal["counter_id"]) == ("S1", "B1")
    assert proposal["physical_stone_identity_verified"] is False
    assert proposal["exact_release_time_verified"] is False
    assert proposal["simulation_ready"] is False


def test_unmatched_or_ambiguous_evidence_abstains():
    fused, held = sample()
    fused["unassociated_counter_events"][0]["colour"] = "yellow"
    result = propose_held_origin_rescues(fused, [held])
    assert result["proposals"] == []
    assert result["passage_audit"][0]["status"] == "no_counter_match"
    fused["unassociated_counter_events"][0]["colour"] = "red"
    fused["unassociated_counter_events"].append(
        {"counter_id": "B2", "colour": "red", "counter_update_s": 31.0})
    result = propose_held_origin_rescues(fused, [held])
    assert result["proposals"] == []
    assert result["passage_audit"][0]["status"] == "ambiguous_counters"


def test_competing_passages_or_existing_shot_abstain():
    fused, held = sample()
    second = deepcopy(held)
    second["shot_id"] = "S2"
    result = propose_held_origin_rescues(fused, [held, second])
    assert result["proposals"] == []
    assert {row["status"] for row in result["passage_audit"]} == {
        "competing_held_passages"}
    fused["events"].append({"shot_id": "S1", "counter_id": None})
    result = propose_held_origin_rescues(fused, [held])
    assert result["proposals"] == []
    assert result["passage_audit"][0]["status"] == "existing_fused_shot"


def test_duplicate_counter_is_rejected():
    fused, held = sample()
    fused["unassociated_counter_events"].append(
        deepcopy(fused["unassociated_counter_events"][0]))
    with pytest.raises(ValueError, match="Duplicate unassociated counter"):
        propose_held_origin_rescues(fused, [held])
