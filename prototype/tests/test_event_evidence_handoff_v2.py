import copy

import pytest

from prototype.event_evidence_handoff_v2 import join_event_evidence


def fixture():
    event = {
        "event_id": "SOURCE-S3",
        "candidate_class": "source_only_two_view_release_provisional",
        "source_shot_ids": ["S3", "S4"],
        "counter_id": None,
        "colour": "red",
        "colour_status": "two_view_source_colour_agrees_identity_unverified",
        "delivery_window_s": [20, 30],
        "attached_held_evidence": {"release_cue_s": 24},
    }
    proposal = {"origin_shot_id": "S3", "release_cue_s": 24, "observed_colour": "red"}
    receiving = {
        "origin_shot_id": "S3",
        "release_cue_s": 24,
        "decision": {"status": "unique_strict_postcut_motion", "colour": "red"},
        "source_colour_agreement": True,
        "physical_stone_identity_verified": False,
        "tracks": {"red": {"strict": [{"time_interval_s": [30.2, 35]}]}},
    }
    review = {
        "event_id": "SOURCE-S3",
        "candidate_class": "source_only_two_view_release_provisional",
        "delivery_window_s": [20, 30],
        "review_window_s": [18, 40],
    }
    return event, proposal, receiving, review


def test_preserves_source_cue_and_explicitly_unverified_physical_state():
    event, proposal, receiving, review = fixture()
    rows = join_event_evidence([event], [], [], [proposal], [receiving], [], [review])
    assert rows[0]["release_cue"]["time_s"] == 24
    assert rows[0]["receiving_view"]["motion_interval_s"] == [30.2, 35]
    assert rows[0]["physical_release_time_s"] is None
    assert rows[0]["persistent_stone_id"] is None
    assert rows[0]["simulation_ready"] is False


def test_rejects_source_rescue_with_physical_identity_claim():
    event, proposal, receiving, review = fixture()
    receiving = copy.deepcopy(receiving)
    receiving["physical_stone_identity_verified"] = True
    with pytest.raises(ValueError, match="Source-only rescue evidence mismatch"):
        join_event_evidence([event], [], [], [proposal], [receiving], [], [review])


def test_rejects_board_cue_that_disagrees_with_scoped_event_cue():
    event = {
        "event_id": "VISUAL-S1",
        "candidate_class": "visual_origin_existing",
        "source_shot_ids": ["S1"],
        "counter_id": "B1",
        "colour": "red",
        "colour_status": "resolved",
        "delivery_window_s": [0, 10],
    }
    release = {
        "event_id": "VISUAL-S1",
        "unique_release_cue_s": 5,
        "unique_passage_colour": "red",
        "origin_shot_id": "S1",
        "scope_status": "unique_passage",
        "scope_route": "existing_single_shot_window",
    }
    board = {
        "provisional_event_id": "VISUAL-S1",
        "event_join_status": "unique_shared_counter",
        "within_view_release_cue_s": 6,
        "physical_stone_to_board_identity_verified": False,
        "physical_state_transition_verified": False,
    }
    review = {
        "event_id": "VISUAL-S1",
        "candidate_class": "visual_origin_existing",
        "delivery_window_s": [0, 10],
        "review_window_s": [0, 15],
    }
    with pytest.raises(ValueError, match="Board and event release cue differ"):
        join_event_evidence([event], [release], [], [], [], [board], [review])
