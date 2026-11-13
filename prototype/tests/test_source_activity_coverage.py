"""Coverage accounting cannot silently turn static-panel video into support."""

import pytest

from source_activity_coverage import overlay_active_static_left


def fixture():
    timeline = {
        "source_id": "recording",
        "source_sha256": "a" * 64,
        "source_interval_s": [0, 300],
        "supported_runs": [{"id": "R1", "layout": "split_2024", "interval_s": [30, 270]}],
        "coverage_gaps_s": [[0, 30], [270, 300]],
        "observed_events": [
            {"id": "E1", "crossing_time_s": 50},
            {"id": "E2", "crossing_time_s": 120},
        ],
    }
    audit = {
        "source_sha256": "a" * 64,
        "static_left_runs": [
            {"start_s": 100, "stop_s": 200, "median_left_mae": 1.5, "median_right_mae": 12.0},
            {"start_s": 250, "stop_s": 300, "median_left_mae": 1.0, "median_right_mae": 1.0},
        ],
    }
    return timeline, audit


def test_active_static_split_preserves_events_and_seconds():
    result = overlay_active_static_left(*fixture())
    assert result["newly_unsupported_seconds"] == 100
    assert result["revised_supported_seconds"] == 140
    assert result["revised_unknown_seconds"] == 160
    assert [row["interval_s"] for row in result["revised_supported_runs"]] == [
        [30, 100],
        [200, 270],
    ]
    assert result["newly_unsupported_intervals"][0]["existing_event_ids_inside"] == ["E2"]
    assert result["original_event_count_unchanged"] == 2


def test_mismatched_source_rejected():
    timeline, audit = fixture()
    audit["source_sha256"] = "b" * 64
    with pytest.raises(ValueError, match="fingerprints differ"):
        overlay_active_static_left(timeline, audit)


def test_audit_interval_must_cover_scored_timeline():
    timeline, audit = fixture()
    audit["source_interval_s"] = [30, 270]
    with pytest.raises(ValueError, match="does not cover"):
        overlay_active_static_left(timeline, audit)


def test_beijing_run_is_not_flagged_by_split_panel_activity():
    timeline, audit = fixture()
    timeline["supported_runs"][0]["layout"] = "beijing_2022"
    result = overlay_active_static_left(timeline, audit)
    assert result["newly_unsupported_seconds"] == 0
    assert result["revised_supported_seconds"] == 240


def test_timeline_hole_rejected():
    timeline, audit = fixture()
    timeline["coverage_gaps_s"][0] = [0, 20]
    with pytest.raises(ValueError, match="overlap or gap"):
        overlay_active_static_left(timeline, audit)
