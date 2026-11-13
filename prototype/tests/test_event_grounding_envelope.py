import pytest

from event_grounding_envelope import ground_event_candidates


def event(shot_id):
    return {
        "shot_id": shot_id,
        "delivery_window_s": [10, 20],
        "colour": "red",
        "colour_provenance": {"basis": "visual_only"},
    }


def edit(shot_id, time_s, tracks=()):
    return {
        "shot_id": shot_id,
        "time_s": time_s,
        "crossing_same_shot_cap_track_count": len(tracks),
        "crossing_same_shot_cap_track_ids": list(tracks),
    }


def temporal(shot_id, time_s, isolated):
    return {"shot_id": shot_id, "time_s": time_s, "isolated_spike": isolated}


def test_envelope_keeps_event_and_marks_possible_identity_break():
    original = [event("S1"), event("S2")]
    enriched = ground_event_candidates(
        original, [edit("S1", 14, ["S1-R01"])], [temporal("S1", 14, True)]
    )
    assert enriched[0]["camera_boundary_evidence"] == {
        "possible_internal_edits": [
            {
                "time_s": 14,
                "evidence_tier": "isolated_spike",
                "crossing_same_shot_cap_track_ids": ["S1-R01"],
                "boundary_status": "possible_unverified",
            }
        ],
        "continuity_status": "possible_edit_crosses_cap_track",
        "physical_stone_identity_verified": False,
    }
    assert enriched[1]["camera_boundary_evidence"]["continuity_status"] == (
        "no_proposed_internal_edit"
    )
    assert enriched[0]["simulation_handoff"]["simulation_ready"] is False
    assert enriched[0]["simulation_handoff"]["delivered_stone_identity"] is None
    assert "camera_boundary_evidence" not in original[0]


def test_possible_edit_without_track_crossing_does_not_claim_continuity():
    enriched = ground_event_candidates([event("S1")], [edit("S1", 15)], [temporal("S1", 15, False)])
    evidence = enriched[0]["camera_boundary_evidence"]
    assert evidence["continuity_status"] == "possible_edit_without_crossing_cap_track"
    assert evidence["physical_stone_identity_verified"] is False
    assert evidence["possible_internal_edits"][0]["evidence_tier"] == ("nonisolated_change")


def test_mismatched_temporal_rows_fail_closed():
    with pytest.raises(ValueError, match="rows differ"):
        ground_event_candidates([event("S1")], [edit("S1", 14)], [])
    with pytest.raises(ValueError, match="outside event window"):
        ground_event_candidates([event("S1")], [edit("S1", 21)], [temporal("S1", 21, True)])
