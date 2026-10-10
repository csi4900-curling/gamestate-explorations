from copy import deepcopy

import pytest

from prototype.full_match_display_join import attach_display_context


def fixture_inputs():
    union = {
        "source_sha256": "source",
        "input_sha256": {"raw": "raw"},
        "raw_candidates": [
            {
                "candidate_id": "S1",
                "passage_time_s": 10.0,
                "tier": "screen_provisional",
                "simulation_ready": False,
            },
            {
                "candidate_id": "S2",
                "passage_time_s": 20.0,
                "tier": "pre_split_review_only",
                "simulation_ready": False,
            },
        ],
    }
    display = {
        "source_sha256": "source",
        "raw_sha256": "raw",
        "events": [
            {
                "event_id": "S1",
                "crossing_time_s": 10.0,
                "display_context_status": "bracketed_display_end",
                "displayed_end": 2,
                "physical_end": None,
            },
            {
                "event_id": "S2",
                "crossing_time_s": 20.0,
                "display_context_status": "bracketed_display_change",
                "displayed_end": None,
                "physical_end": None,
            },
        ],
    }
    return union, display


def test_keeps_displayed_end_separate_from_physical_end():
    union, display = fixture_inputs()
    result = attach_display_context(union, display)
    assert result["bracketed_candidate_tiers_by_displayed_end"] == {"2": {"screen_provisional": 1}}
    assert result["raw_candidates"][0]["physical_end_identity"] is None
    assert result["raw_candidates"][1]["broadcast_display_context"]["displayed_end"] is None


def test_rejects_missing_candidate_context_and_timestamp_drift():
    union, display = fixture_inputs()
    missing = deepcopy(display)
    missing["events"].pop()
    with pytest.raises(ValueError, match="cover every"):
        attach_display_context(union, missing)
    display["events"][1]["crossing_time_s"] = 21.0
    with pytest.raises(ValueError, match="timestamps"):
        attach_display_context(union, display)
