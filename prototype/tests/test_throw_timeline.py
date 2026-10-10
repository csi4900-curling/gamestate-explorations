"""Partial timelines must retain gaps and reject mismatched adapter evidence."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from throw_timeline import assemble_timeline


def fixture():
    runs = [
        {"layout": "split_2024", "interval_s": [0, 300], "samples": 30},
        {"layout": "unknown", "interval_s": [300, 600], "samples": 30},
        {"layout": "split_2024", "interval_s": [600, 900], "samples": 30},
    ]
    preflight = {
        "source_id": "source",
        "source_sha256": "digest",
        "source_interval_s": [0, 900],
        "runs": runs,
        "coverage_gaps_s": [[300, 600]],
    }
    completed = [
        (
            runs[0],
            {
                "source_id": "source",
                "source_sha256": "digest",
                "source_interval_s": [0, 300],
                "events": [{"id": "S01", "crossing_time_s": 100, "colour": "red"}],
            },
            "run-01/events.json",
        ),
        (
            runs[2],
            {
                "source_id": "source",
                "source_sha256": "digest",
                "source_interval_s": [600, 900],
                "events": [{"id": "S01", "crossing_time_s": 700, "colour": "yellow"}],
            },
            "run-03/events.json",
        ),
    ]
    return preflight, completed


def test_partial_timeline_keeps_gap_and_run_scoped_event_ids():
    preflight, completed = fixture()
    result = assemble_timeline(preflight, completed)
    assert result["status"] == "partial_coverage"
    assert result["coverage_gaps_s"] == [[300, 600]]
    assert [event["id"] for event in result["observed_events"]] == ["R01-S01", "R02-S01"]
    assert "events" not in result
    assert [event["boundary_review_required"] for event in result["observed_events"]] == [
        False,
        False,
    ]


def test_rejects_event_outside_supported_run():
    preflight, completed = fixture()
    completed[1][1]["events"][0]["crossing_time_s"] = 500
    with pytest.raises(ValueError, match="outside"):
        assemble_timeline(preflight, completed)


def test_rejects_wrong_source_fingerprint():
    preflight, completed = fixture()
    completed[0][1]["source_sha256"] = "different"
    with pytest.raises(ValueError, match="fingerprint"):
        assemble_timeline(preflight, completed)


def test_flags_event_near_run_boundary():
    preflight, completed = fixture()
    completed[1][1]["events"][0]["crossing_time_s"] = 605
    result = assemble_timeline(preflight, completed)
    assert result["observed_events"][1]["boundary_review_required"] is True
    assert result["observed_events"][1]["seconds_from_run_boundary"] == 5
