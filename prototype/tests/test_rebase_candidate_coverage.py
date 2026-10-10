from copy import deepcopy

import pytest

from prototype.rebase_candidate_coverage import rebase_candidate_coverage


def fixtures():
    sequence = {"source_sha256": "a" * 64,
                "supported_runs": [{"id": "R01", "interval_s": [10, 60]}],
                "coverage_gaps_s": [[0, 10], [60, 70]],
                "right_proposals": [{"run_id": "R01", "passage_time_s": 45}],
                "rows": [{"candidate_id": "left:R01-S1", "left_event_id": "R01-S1",
                          "observation_kind": "left_tracked_passage",
                          "observation_time_s": 40},
                         {"candidate_id": "right:R01:A1",
                          "observation_kind": "right_observed_motion_passage",
                          "observation_time_s": 45}],
                "complete_throw_sequence_verified": False}
    overlay = {"source_sha256": "a" * 64,
               "supported_runs": [{"id": "R01", "layout": "split_2024",
                                   "interval_s": [10, 50]}],
               "coverage_gaps_s": [[0, 10], [50, 70]]}
    return sequence, overlay


def test_coverage_rebase_preserves_candidates_and_updates_gaps():
    sequence, overlay = fixtures()
    original = deepcopy(sequence)
    result = rebase_candidate_coverage(sequence, overlay)
    assert result["coverage_gaps_s"] == [[0, 10], [50, 70]]
    assert result["rows"] == original["rows"]
    assert sequence == original


def test_coverage_rebase_rejects_candidate_in_removed_tail():
    sequence, overlay = fixtures()
    sequence["rows"][0]["observation_time_s"] = 55
    with pytest.raises(ValueError, match="Candidate leaves"):
        rebase_candidate_coverage(sequence, overlay)
