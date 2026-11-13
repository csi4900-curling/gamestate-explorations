import copy

import pytest

from prototype.preorigin_travel_union import append_preorigin_travel_rescues


def proposal():
    return {
        "proposal_id": "TRAVEL-B02",
        "origin_shot_id": "S27",
        "origin_shot_interval_s": [356, 365.4],
        "receiving_shot_id": "S28",
        "receiving_shot_interval_s": [365.4, 382.2],
        "receiving_track": {
            "colour": "red",
            "interval_s": [365.4, 380.2],
            "span_px": 223.46,
            "point_count": 65,
        },
        "counter_id": "B02",
        "counter_colour": "red",
        "counter_time_s": 383,
        "visible_release_cue_s": None,
        "physical_stone_identity_verified": False,
        "simulation_ready": False,
    }


def test_adds_travel_candidate_without_inventing_release():
    rows = append_preorigin_travel_rescues([], [proposal()])
    assert rows[0]["event_id"] == "TRAVEL-B02"
    assert rows[0]["source_shot_ids"] == ["S27", "S28"]
    assert rows[0]["visible_release_cue_s"] is None
    assert rows[0]["physical_stone_identity_verified"] is False


def test_rejects_duplicate_counter_and_shot():
    old = {
        "event_id": "VISUAL-S25",
        "source_shot_ids": ["S25"],
        "counter_id": "B02",
        "delivery_window_s": [250, 330],
        "observed_travel_window_s": None,
    }
    with pytest.raises(ValueError, match="duplicates"):
        append_preorigin_travel_rescues([old], [proposal()])
    old["counter_id"] = None
    old["source_shot_ids"] = ["S28"]
    with pytest.raises(ValueError, match="duplicates"):
        append_preorigin_travel_rescues([old], [proposal()])


def test_rejects_counter_before_receiving_view_ends():
    item = copy.deepcopy(proposal())
    item["counter_time_s"] = 380
    with pytest.raises(ValueError, match="not ordered"):
        append_preorigin_travel_rescues([], [item])
