import pytest

from prototype.shot_scoped_release import select_event_release


def passage(time, colour="red"):
    return {
        "colour": colour,
        "held_interval_s": [time - 1, time - 0.2],
        "release_cue_s": time,
        "moving_interval_s": [time, time + 0.2],
    }


def test_travel_without_declared_origin_abstains_even_with_broad_cue():
    event = {
        "event_id": "TRAVEL-B48",
        "candidate_class": "counter_linked_travel_only_provisional",
        "source_shot_ids": ["S244"],
        "attached_held_evidence": None,
    }
    result = select_event_release(event, {"passages": [passage(3121.4)]}, {})
    assert result["scope_status"] == "no_attached_origin_shot"
    assert result["unique_release_cue_s"] is None


def test_attached_held_shot_resolves_broad_window_ambiguity():
    event = {
        "event_id": "TRAVEL-B57",
        "candidate_class": "counter_linked_travel_only_provisional",
        "source_shot_ids": ["S279", "S278"],
        "attached_held_evidence": {"shot_id": "S278"},
    }
    scoped = {
        "TRAVEL-B57": {
            "held_shot_id": "S278",
            "held_shot_interval_s": [3452.2, 3464.0],
            "scoped_scan": {"passages": [passage(3459.8)]},
        }
    }
    result = select_event_release(
        event, {"passages": [passage(3452.2), passage(3459.8)]}, {"S278": [3452.2, 3464.0]}, scoped
    )
    assert result["scope_status"] == "unique_passage"
    assert result["unique_release_cue_s"] == 3459.8


def test_reject_passage_crossing_declared_shot_boundary():
    event = {
        "event_id": "VISUAL-S1",
        "candidate_class": "visual_origin_existing",
        "source_shot_ids": ["S1"],
        "delivery_window_s": [10, 20],
    }
    broad = {"delivery_window_s": [10, 20], "passages": [passage(19.9)]}
    with pytest.raises(ValueError, match="crosses"):
        select_event_release(event, broad, {"S1": [10, 20]})
