"""Provisional two-view observations cannot become verified game state."""

from copy import deepcopy

import pytest

from prototype.cross_view_bridge_evidence import build_cross_view_bridge_evidence


def fixture_inputs():
    episode = {
        "source": "estonia", "motion_episode": {
            "direction": "positive_y", "physical_release_verified": False,
            "moving_run_interval_s": [10, 11],
            "motion_onset_observation_bracket_s": [10, 11],
            "pre_onset_observation_count": 5},
        "continuation": {
            "same_stone_identity_verified": False, "physical_stop_verified": False,
            "points": [{"time_s": 10, "center_1080p_px": [100, 100]},
                       {"time_s": 11, "center_1080p_px": [100, 200]}]}}
    edge = {
        "video_sha256": "source", "rois_xyxy_1080p": {},
        "yellow_pixel_threshold": 50,
        "summary": {"simultaneous_threshold_frames": 2},
        "frames": [{"source_time_s": t,
                    "yellow_visible_by_threshold": {"left_entry": True,
                                                    "right_exit": True}}
                   for t in (11.5, 11.6)]}
    bridge = {
        "video_sha256": "source", "rows": [
            {"source_time_s": 12, "chosen": {"center_1080p_px": [105, 10]}},
            {"source_time_s": 13, "chosen": {"center_1080p_px": [110, 50]}}],
        "prior_s02_overlap": [{"source_time_s": 13,
                               "new_contour_center_1080p_px": [110, 50],
                               "prior_s02_pixel_center": [110, 50]}],
        "mean_overlap_center_distance_px": 0,
        "maximum_overlap_center_distance_px": 0}
    candidate = {
        "source_sha256": "source", "candidate_id": "S02", "colour": "yellow",
        "crossing_time_s": 12.5,
        "cases": {"base": {"selection": {"path": [
            {"source_time_s": 13, "pixel_center": [110, 50]}]}}}}
    return episode, edge, bridge, candidate


def test_keeps_observations_but_no_physical_state_claim():
    row = build_cross_view_bridge_evidence(*fixture_inputs())
    assert row["handoff"]["simultaneous_yellow_edge_frame_count"] == 2
    assert row["left_view"]["prior_candidate_path_overlap_count"] == 1
    assert row["right_view"]["pre_onset_prefix_excluded"] == 5
    assert row["handoff"]["physical_stone_identity_verified"] is False
    assert row["game_state_after"]["complete_board"] is None
    assert row["game_state_after"]["simulation_ready"] is False


def test_keeps_a_right_view_contour_after_the_body_seed():
    inputs = fixture_inputs()
    inputs[0]["continuation"]["points"].append(
        {"time_s": 11.2, "center_1080p_px": [100, 250]})
    row = build_cross_view_bridge_evidence(*inputs)
    assert row["right_view"]["samples"][-1]["source_time_s"] == 11.2
    assert row["right_view"]["end_status"] == "right_panel_exit_no_observed_stop"


def test_rejects_source_mismatch_and_invalid_edge_overlap():
    inputs = fixture_inputs()
    mismatched = deepcopy(inputs)
    mismatched[2]["video_sha256"] = "other"
    with pytest.raises(ValueError, match="source video"):
        build_cross_view_bridge_evidence(*mismatched)
    no_overlap = deepcopy(inputs)
    no_overlap[1]["frames"][1]["yellow_visible_by_threshold"]["right_exit"] = False
    with pytest.raises(ValueError, match="Edge overlap"):
        build_cross_view_bridge_evidence(*no_overlap)


def test_rejects_overlap_that_does_not_match_source_track():
    inputs = fixture_inputs()
    inputs[2]["prior_s02_overlap"][0]["new_contour_center_1080p_px"] = [100, 50]
    with pytest.raises(ValueError, match="left contour track"):
        build_cross_view_bridge_evidence(*inputs)
