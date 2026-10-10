"""Export a provisional two-camera stone observation without asserting game truth."""

from math import dist


def build_cross_view_bridge_evidence(episode, edge, left_bridge, left_candidate):
    """Join preserved observations; reject inconsistent provenance or chronology."""
    source_hash = edge["video_sha256"]
    if left_bridge["video_sha256"] != source_hash or left_candidate["source_sha256"] != source_hash:
        raise ValueError("Two-view inputs do not share source video bytes")
    if not episode["source"] or not left_candidate["candidate_id"]:
        raise ValueError("Missing episode source or left candidate ID")
    if left_candidate["colour"] != "yellow":
        raise ValueError("Two-view colour claim differs")

    motion = episode["motion_episode"]
    right = episode["continuation"]
    if (
        motion["direction"] not in ("positive_y", "negative_y")
        or motion["physical_release_verified"]
        or right["same_stone_identity_verified"]
        or right["physical_stop_verified"]
    ):
        raise ValueError("Right episode is not a provisional downward motion")
    right_points = right["points"]
    left_rows = left_bridge["rows"]
    if not right_points or not left_rows or any(row["chosen"] is None for row in left_rows):
        raise ValueError("Missing observed path sample")
    right_times = [row["time_s"] for row in right_points]
    left_times = [row["source_time_s"] for row in left_rows]
    if (
        right_times != sorted(set(right_times))
        or left_times != sorted(set(left_times))
        or right_times[-1] >= left_times[0]
    ):
        raise ValueError("Path chronology disagrees")
    if (
        motion["moving_run_interval_s"][0] != right_times[0]
        or motion["moving_run_interval_s"][1] > right_times[-1]
        or left_candidate["crossing_time_s"] <= left_times[0]
    ):
        raise ValueError("Motion/crossing chronology disagrees")

    both = [
        row["source_time_s"]
        for row in edge["frames"]
        if all(row["yellow_visible_by_threshold"].values())
    ]
    summary = edge["summary"]
    if (
        len(both) != summary["simultaneous_threshold_frames"]
        or not both
        or not right_times[-1] <= both[0] <= left_times[0] + 1
        or both[-1] >= left_candidate["crossing_time_s"]
    ):
        raise ValueError("Edge overlap is inconsistent with the observed paths")

    prior_path = left_candidate["cases"]["base"]["selection"]["path"]
    prior_by_time = {row["source_time_s"]: row for row in prior_path}
    left_by_time = {row["source_time_s"]: row for row in left_rows}
    overlap = left_bridge["prior_s02_overlap"]
    if not overlap or len(prior_by_time) != len(prior_path) or len(left_by_time) != len(left_rows):
        raise ValueError("No unambiguous prior left-path overlap")
    distances = []
    for row in overlap:
        timestamp = row["source_time_s"]
        if timestamp not in prior_by_time:
            raise ValueError("Overlap time is absent from prior left path")
        prior = prior_by_time[timestamp]["pixel_center"]
        if row["prior_s02_pixel_center"] != prior:
            raise ValueError("Prior path coordinates changed")
        if (
            timestamp not in left_by_time
            or row["new_contour_center_1080p_px"]
            != left_by_time[timestamp]["chosen"]["center_1080p_px"]
        ):
            raise ValueError("Overlap coordinates differ from left contour track")
        distances.append(dist(row["new_contour_center_1080p_px"], prior))
    if (
        abs(sum(distances) / len(distances) - left_bridge["mean_overlap_center_distance_px"])
        > 0.001
        or abs(max(distances) - left_bridge["maximum_overlap_center_distance_px"]) > 0.001
    ):
        raise ValueError("Left-path overlap statistics changed")

    return {
        "candidate_id": left_candidate["candidate_id"],
        "source_video_sha256": source_hash,
        "status": "postreview_provisional_two_view_observation_bridge",
        "colour_claim": left_candidate["colour"],
        "right_view": {
            "coordinate_frame": "source_1080p_full_frame_pixels",
            "observed_motion_onset_bracket_s": motion["motion_onset_observation_bracket_s"],
            "direction_image_y": motion["direction"],
            "pre_onset_prefix_excluded": motion["pre_onset_observation_count"],
            "samples": [
                {"source_time_s": row["time_s"], "pixel_center": row["center_1080p_px"]}
                for row in right_points
            ],
            "end_status": "right_panel_exit_no_observed_stop",
        },
        "handoff": {
            "simultaneous_yellow_edge_frame_count": len(both),
            "simultaneous_yellow_edge_interval_s": [both[0], both[-1]],
            "edge_rois_xyxy_1080p": edge["rois_xyxy_1080p"],
            "edge_pixel_threshold": edge["yellow_pixel_threshold"],
            "roi_selected_after_source_review": True,
            "physical_stone_identity_verified": False,
        },
        "left_view": {
            "coordinate_frame": "source_1080p_full_frame_pixels",
            "samples": [
                {
                    "source_time_s": row["source_time_s"],
                    "yellow_cap_pixel_center": row["chosen"]["center_1080p_px"],
                }
                for row in left_rows
            ],
            "prior_candidate_path_overlap_count": len(overlap),
            "prior_candidate_path_mean_center_difference_px": round(
                sum(distances) / len(distances), 3
            ),
            "prior_candidate_path_max_center_difference_px": round(max(distances), 3),
            "prior_candidate_path_metric_accuracy_verified": False,
        },
        "candidate_crossing_time_s": left_candidate["crossing_time_s"],
        "candidate_crossing_is_release": False,
        "game_state_after": {
            "physical_throw_verified": False,
            "end_identity": None,
            "official_shot_identity": None,
            "release_time_s": None,
            "settle_time_s": None,
            "complete_board": None,
            "persistent_stone_ids": None,
            "metric_trajectory": None,
            "spin_revolution_count": None,
            "simulation_ready": False,
        },
    }
