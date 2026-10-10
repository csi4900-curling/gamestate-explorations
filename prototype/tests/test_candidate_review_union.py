"""All raw left proposals and right-only entries survive the review handoff."""

import pytest

from candidate_review_union import build_candidate_review_union


def fixture():
    timeline = {
        "source_id": "match",
        "source_sha256": "source",
        "source_interval_s": [0, 100],
        "supported_runs": [{"id": "R01", "layout": "split_2024", "interval_s": [0, 100]}],
        "observed_events": [
            {
                "id": "R01-S01",
                "source_event_id": "S01",
                "source_run_id": "R01",
                "colour": "red",
                "crossing_time_s": 10,
            }
        ],
    }
    left = {
        "R01": [
            {
                "id": "S01",
                "colour": "red",
                "crossing_time_s": 10,
                "disposition": "auto_confirmed_candidate",
                "stage_evidence": [],
                "observed_motion_interval_s": [9, 11],
            },
            {
                "id": "S02",
                "colour": "yellow",
                "crossing_time_s": 20,
                "disposition": "needs_review",
                "stage_evidence": [{"reason": "motion"}],
                "observed_motion_interval_s": [19, 21],
            },
        ]
    }
    fusion = {
        "source_sha256": "source",
        "right_entries": [
            {
                "right_entry_id": "I01:R001",
                "right_raw_track_id": "R001",
                "right_entry_time_s": 15,
                "right_colour_claim": "red",
                "right_observed_prefix_interval_s": [14, 17],
                "fusion_status": "cross_view_time_colour_corrob",
                "conditional_left_candidate_id": "R01-S01",
            },
            {
                "right_entry_id": "I02:R001",
                "right_raw_track_id": "R001",
                "right_entry_time_s": 30,
                "right_colour_claim": "yellow",
                "right_observed_prefix_interval_s": [29, 33],
                "fusion_status": "right_only_left_static_review",
                "conditional_left_candidate_id": None,
            },
        ],
    }
    return timeline, left, fusion


def test_union_preserves_withheld_left_and_distinct_right_only_review():
    result = build_candidate_review_union(*fixture())
    assert result["candidate_count"] == 3
    assert [row["candidate_id"] for row in result["candidates"]] == [
        "R01-S01",
        "R01-S02",
        "RIGHT-I02:R001",
    ]
    assert result["candidates"][0]["right_entry_ids"] == ["I01:R001"]
    assert result["candidates"][0]["observed_motion_interval_s"] == [9, 11]
    assert result["candidates"][0]["corroborating_right_motion_intervals_s"] == [[14, 17]]
    assert result["candidates"][2]["observed_motion_interval_s"] == [29, 33]
    assert result["candidates"][1]["left_stage_evidence"] == [{"reason": "motion"}]
    assert all(
        not row["simulation_ready"] and not row["physical_throw_verified"]
        for row in result["candidates"]
    )


def test_union_rejects_accepted_left_event_missing_from_raw_triage():
    timeline, left, fusion = fixture()
    left["R01"] = left["R01"][1:]
    with pytest.raises(ValueError, match="lack a left proposal"):
        build_candidate_review_union(timeline, left, fusion)


def test_beijing_adapter_event_keeps_distinct_evidence_status():
    timeline, _, fusion = fixture()
    timeline["supported_runs"][0]["layout"] = "beijing_2022"
    result = build_candidate_review_union(timeline, {}, fusion)
    assert result["candidates"][0]["review_status"] == "beijing_adapter_candidate"
    assert result["candidates"][0]["origin"] == "beijing_adapter_observation"
