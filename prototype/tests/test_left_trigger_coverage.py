import copy
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from left_trigger_coverage import attach_left_trigger_coverage


def fixtures():
    handoff = {
        "source_sha256": "video", "input_sha256": {"timeline": "timeline"},
        "supported_runs": [{"id": "R01", "interval_s": [10, 50]}],
        "rows": [
            {"candidate_id": "L1", "observation_time_s": 20,
             "observation_kind": "left_tracked_passage"},
            {"candidate_id": "R1", "observation_time_s": 30,
             "observation_kind": "right_observed_motion_passage"},
        ], "limitations": [], "complete_throw_sequence_verified": False,
    }
    activity = {
        "source_sha256": "video", "timeline_sha256": "timeline",
        "newly_unsupported_seconds": 10,
        "newly_unsupported_intervals": [
            {"source_run_id": "R01", "interval_s": [25, 35],
             "reason": "left_panel_static_while_right_panel_active",
             "median_left_mae": 1.2, "median_right_mae": 16.3}],
    }
    return handoff, activity


def test_preserves_right_candidate_and_splits_left_support():
    handoff, activity = fixtures()
    result = attach_left_trigger_coverage(handoff, activity)
    assert result["left_trigger_blind_seconds"] == 10
    assert [r["interval_s"] for r in result["left_trigger_supported_intervals"]] == [
        [10, 25], [35, 50]]
    assert result["right_view_candidate_ids_in_left_trigger_blind_interval"] == ["R1"]
    assert result["rows"][1]["left_trigger_coverage"] == (
        "source_activity_blind_right_view_observation_only")
    assert handoff["rows"][1].get("left_trigger_coverage") is None


def test_rejects_source_mismatch_and_left_candidate_in_blind():
    handoff, activity = fixtures()
    activity["source_sha256"] = "other"
    with pytest.raises(ValueError, match="Source videos differ"):
        attach_left_trigger_coverage(handoff, activity)
    activity["source_sha256"] = "video"
    changed = copy.deepcopy(handoff)
    changed["rows"][0]["observation_time_s"] = 30
    with pytest.raises(ValueError, match="Left-trigger event inside"):
        attach_left_trigger_coverage(changed, activity)


def test_rejects_out_of_run_and_overlap():
    handoff, activity = fixtures()
    activity["newly_unsupported_intervals"][0]["interval_s"] = [25, 51]
    with pytest.raises(ValueError, match="outside refined routed support"):
        attach_left_trigger_coverage(handoff, activity)
    activity["newly_unsupported_intervals"][0]["interval_s"] = [25, 35]
    activity["newly_unsupported_intervals"].append({
        **activity["newly_unsupported_intervals"][0], "interval_s": [34, 40]})
    with pytest.raises(ValueError, match="Overlapping blind intervals"):
        attach_left_trigger_coverage(handoff, activity)


def test_rejects_inconsistent_activity_duration():
    handoff, activity = fixtures()
    activity["newly_unsupported_seconds"] = 9
    with pytest.raises(ValueError, match="duration does not match"):
        attach_left_trigger_coverage(handoff, activity)
