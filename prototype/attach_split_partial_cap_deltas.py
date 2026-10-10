"""Attach partial pre/post image deltas to an evidence sequence."""

from collections import Counter
from copy import deepcopy


def attach_deltas(partial_sequence, pre_scan, delta):
    source = partial_sequence["source_sha256"]
    if pre_scan["source_sha256"] != source or delta["source_sha256"] != source:
        raise ValueError("Source fingerprints differ")
    left_rows = {row["candidate_id"]: row for row in partial_sequence["rows"]
                 if row["observation_kind"] == "left_tracked_passage"}
    pre_by_id = {row["candidate_id"]: row for row in pre_scan["rows"]}
    delta_by_id = {row["candidate_id"]: row for row in delta["rows"]}
    if (len(left_rows) != partial_sequence["left_candidate_count"]
            or len(pre_by_id) != len(pre_scan["rows"])
            or len(delta_by_id) != len(delta["rows"])
            or set(left_rows) != set(pre_by_id) or set(left_rows) != set(delta_by_id)):
        raise ValueError("Pre scan and delta must cover every left candidate exactly once")
    result = deepcopy(partial_sequence)
    for row in result["rows"]:
        cid = row["candidate_id"]
        if cid not in left_rows:
            row["pre_candidate_partial_cap_observation"] = None
            row["partial_cap_image_transition"] = None
            continue
        before = pre_by_id[cid]
        change = delta_by_id[cid]
        if (before["left_event_id"] != row["left_event_id"]
                or before["observed_left_passage_time_s"] != row["observation_time_s"]
                or change["pre_observation_status"] != before["observation_status"]
                or change["post_observation_status"] != row[
                    "post_candidate_partial_cap_observation"]["status"]
                or before["complete_board_verified"]
                or change["physical_transition_verified"]
                or change["complete_board_verified"]
                or change["simulation_ready"]):
            raise ValueError("Pre/delta evidence conflicts or promotes physical state")
        row["pre_candidate_partial_cap_observation"] = {
            "status": before["observation_status"],
            "sample_times_s": before["sample_times_s"],
            "scene_mae_between_samples": before["scene_mae_between_samples"],
            "coordinate_frame": before["coordinate_frame"],
            "stable_cap_proposals": before["stable_cap_proposals"],
            "complete_board_verified": False,
        }
        row["partial_cap_image_transition"] = change
        if row["game_state_after"]["complete_board"] is not None:
            raise ValueError("Image delta cannot become a complete game state")
    result["pre_partial_cap_observation_status_counts"] = dict(Counter(
        item["observation_status"] for item in pre_scan["rows"]))
    result["partial_cap_image_transition_status_counts"] = dict(Counter(
        item["comparison_status"] for item in delta["rows"]))
    result["status"] = "candidate_sequence_with_partial_pre_post_cap_image_deltas"
    return result
