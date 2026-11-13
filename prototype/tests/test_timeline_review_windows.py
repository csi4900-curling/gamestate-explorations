"""A review window cannot borrow context from an unsupported video gap."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from timeline_review_windows import build_timeline_review_windows


def test_context_clips_to_supported_run_edges():
    timeline = {
        "source_id": "sample",
        "source_sha256": "digest",
        "source_interval_s": [0, 300],
        "coverage_gaps_s": [[100, 200]],
        "supported_runs": [
            {"id": "R01", "interval_s": [0, 100]},
            {"id": "R02", "interval_s": [200, 300]},
        ],
        "observed_events": [
            {
                "id": "R01-S01",
                "source_run_id": "R01",
                "colour": "red",
                "crossing_time_s": 95,
                "boundary_review_required": True,
            },
            {
                "id": "R02-S01",
                "source_run_id": "R02",
                "colour": "yellow",
                "crossing_time_s": 205,
                "boundary_review_required": True,
            },
        ],
    }
    result = build_timeline_review_windows(timeline)
    first, second = result["review_windows"]
    assert first["review_end_s"] == 100
    assert second["review_start_s"] == 200
    assert first["context_clipped_at_run_end"]
    assert second["context_clipped_at_run_start"]
    assert result["coverage_gaps_s"] == [[100, 200]]


def test_unknown_run_reference_is_rejected():
    timeline = {
        "source_id": "sample",
        "source_sha256": "digest",
        "source_interval_s": [0, 100],
        "coverage_gaps_s": [],
        "supported_runs": [],
        "observed_events": [{"id": "S01", "source_run_id": "missing", "crossing_time_s": 10}],
    }
    with pytest.raises(ValueError, match="unknown run"):
        build_timeline_review_windows(timeline)
