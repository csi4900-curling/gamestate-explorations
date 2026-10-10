from copy import deepcopy

import pytest

from prototype.refine_split_coverage import refined_coverage


def timeline():
    return {"source_interval_s": [0, 100],
            "supported_runs": [
                {"id": "R01", "layout": "split_2024", "interval_s": [10, 60]},
                {"id": "R02", "layout": "split_2024", "interval_s": [70, 95]},
            ],
            "coverage_gaps_s": [[0, 10], [60, 70], [95, 100]],
            "observed_events": [{"id": "R02-S1", "crossing_time_s": 80}]}


def test_refined_cut_extends_explicit_gap_without_mutating_frozen_timeline():
    original = timeline()
    snapshot = deepcopy(original)
    result = refined_coverage(original, "R02", 90)
    assert result["supported_runs"][1]["interval_s"] == [70, 90]
    assert result["coverage_gaps_s"] == [[0, 10], [60, 70], [90, 100]]
    assert result["coverage_gap_duration_s"] == 30
    assert original == snapshot


def test_cut_rejects_candidate_outside_new_support():
    with pytest.raises(ValueError, match="left event"):
        refined_coverage(timeline(), "R02", 79)
