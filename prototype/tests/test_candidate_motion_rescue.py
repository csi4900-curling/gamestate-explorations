from candidate_motion_rescue import (
    BRIDGE_ELIGIBLE, mark_bridge_eligible, rescue_candidate_path,
)
from candidate_motion_rescue_screen import screen_rescue_candidate


def sample(time_s, ys, *, status="original_registered", view="right"):
    return {
        "source_time_s": time_s,
        "status": status,
        "views": {view: {"proposals": [
            {"colour": "red", "ground_position_m": [0.0, y],
             "pixel_center": [100.0, 100.0]}
            for y in ys]}},
    }


def test_dropout_marking_preserves_visible_far_cap_objection():
    rows = [sample(0, [0.5]), sample(0.5, [8.0]),
            sample(1.0, [], status="abstained_no_stable_anchor")]
    marked = mark_bridge_eligible(rows, "red", "right")
    assert marked[0]["status"] == BRIDGE_ELIGIBLE
    assert marked[1]["status"] == "original_registered"
    assert marked[2]["status"] == BRIDGE_ELIGIBLE
    assert rows[0]["status"] == "original_registered"


def test_existing_unique_path_is_preserved_when_rescue_would_be_ambiguous():
    path = [{"source_time_s": 0, "ground_position_m": [0, 13]}]
    original = {"status": "provisional_unique_far_entry_motion_path",
                "path": path, "sample_count": 1}
    decision = rescue_candidate_path(original, [], "red", "right")
    assert decision["rescue_status"] == "baseline_path_preserved"
    assert decision["selection"] == original
    assert decision["selection"] is not original


def test_shared_prefix_stops_before_two_plausible_endings():
    rows = [sample(i * 0.5, [13.0 - i * 0.8]) for i in range(5)]
    rows.append(sample(2.5, [9.0, 8.9]))
    decision = rescue_candidate_path(
        {"status": "no_supported_far_entry_motion_path", "path": []},
        rows, "red", "right")
    selection = decision["selection"]
    assert selection["status"] == "provisional_shared_prefix_motion_evidence"
    assert len(selection["path"]) == 5
    assert selection["first_ambiguity_time_s"] == 2.5
    assert selection["observation_after_prefix_verified"] is False


def test_patch_screen_rejects_a_visually_unsupported_rescue():
    motion = {"candidate_id": "D05", "selection": {
        "status": "provisional_unique_dropout_rescue_motion_path",
        "path": [{"source_time_s": 1}], "sample_count": 1}}
    patch = {"candidate_id": "D05", "samples": [
        {"status": "scored", "patch_accepted": False},
        {"status": "scored", "patch_accepted": False}]}
    decision = screen_rescue_candidate(motion, patch)
    assert not decision["accepted"]
    assert decision["status"] == "motion_without_stone_like_patch_support"
