import copy

import pytest

from prototype.source_release_rescue_union import append_source_release_rescues


def evidence():
    existing = [
        {
            "event_id": "VISUAL-S1",
            "source_shot_ids": ["S1"],
            "delivery_window_s": [0, 10],
            "observed_travel_window_s": None,
        }
    ]
    proposal = {
        "proposal_id": "p",
        "candidate_class": "source_only_held_release_provisional",
        "origin_shot_id": "S3",
        "origin_shot_interval_s": [20, 30],
        "release_cue_s": 24,
        "observed_colour": "red",
        "held_interval_s": [21, 23],
        "below_ice_fraction": 0.8,
    }
    receiving = {
        "proposal_id": "p",
        "origin_shot_id": "S3",
        "receiving_shot_id": "S4",
        "origin_colour": "red",
        "release_cue_s": 24,
        "hard_cut_verified": True,
        "cut_time_s": 30,
        "receiving_window_s": [30.2, 42],
        "decision": {"colour": "red", "status": "unique_strict_postcut_motion"},
        "tracks": {
            "red": {
                "strict": [
                    {
                        "time_interval_s": [30.4, 35],
                        "span_px": 60,
                        "camera_motion_status": "camera_motion_unresolved",
                    }
                ]
            }
        },
        "physical_stone_identity_verified": False,
    }
    return existing, proposal, receiving


def test_adds_source_only_event_without_identity_claim():
    existing, proposal, receiving = evidence()
    rows = append_source_release_rescues(existing, [proposal], [receiving])
    assert len(rows) == 2
    assert rows[-1]["source_shot_ids"] == ["S3", "S4"]
    assert rows[-1]["counter_id"] is None
    assert rows[-1]["physical_stone_identity_verified"] is False
    assert existing == [evidence()[0][0]]


def test_rejects_receiving_shot_already_in_event():
    existing, proposal, receiving = evidence()
    receiving = copy.deepcopy(receiving)
    receiving["receiving_shot_id"] = "S1"
    with pytest.raises(ValueError, match="assigned camera shot"):
        append_source_release_rescues(existing, [proposal], [receiving])


def test_rejects_nonmatching_receiving_colour():
    existing, proposal, receiving = evidence()
    receiving = copy.deepcopy(receiving)
    receiving["decision"]["colour"] = "yellow"
    with pytest.raises(ValueError, match="matching two-view"):
        append_source_release_rescues(existing, [proposal], [receiving])
