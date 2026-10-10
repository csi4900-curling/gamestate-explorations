"""A sampled layout run cannot imply every second had a readable counter."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from reconcile_counter_coverage import compare_route


def test_route_comparison_exposes_unreadable_supported_seconds():
    audit = {
        "source_interval_s": [0, 4],
        "counter_samples": [
            {"time_s": 0, "counts": None},
            {"time_s": 1, "counts": [8, 8]},
            {"time_s": 2, "counts": None},
            {"time_s": 3, "counts": [8, 7]},
        ],
        "counter_events": [{"id": "B01", "colour": "yellow", "crossing_time_s": 3.0,
                            "evidence_interval_s": [1.0, 3.0]}],
    }
    timeline = {"observed_events": [{"id": "R01-B01", "colour": "yellow",
                                     "crossing_time_s": 3.0}]}
    route = {"layout_chunk_s": 2, "coverage_gaps_s": [[0, 2]]}
    result = compare_route(audit, timeline, route)
    assert result["counter_readable_in_declared_unknown_s"] == 1
    assert result["counter_unreadable_in_declared_supported_s"] == 1
    assert result["counter_events_in_declared_unknown"] == []
