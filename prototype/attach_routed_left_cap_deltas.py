"""Attach receiving-view image-cap changes without promoting physical state."""

from collections import Counter
from copy import deepcopy


def attach_routed_left_cap_deltas(sequence, pre_scan, delta):
    source = sequence["source_sha256"]
    if pre_scan["source_sha256"] != source or delta["source_sha256"] != source:
        raise ValueError("Source fingerprints differ")
    left_ids = {row["candidate_id"] for row in sequence["rows"]
                if row.get("post_candidate_receiving_view_observation") is not None
                and row["post_candidate_receiving_view_observation"]["view"] == "left"}
    pre_by_id = {row["candidate_id"]: row for row in pre_scan["rows"]}
    delta_by_id = {row["candidate_id"]: row for row in delta["rows"]}
    if (len(pre_by_id) != len(pre_scan["rows"]) or
            len(delta_by_id) != len(delta["rows"]) or
            set(pre_by_id) != left_ids or set(delta_by_id) != left_ids):
        raise ValueError("Pre/delta coverage differs from routed left rows")
    result = deepcopy(sequence)
    for row in result["rows"]:
        cid = row["candidate_id"]
        receiving = row.get("post_candidate_receiving_view_observation")
        if cid in left_ids:
            before = pre_by_id[cid]
            change = delta_by_id[cid]
            if (change["pre_observation_status"] != before["status"] or
                    change["post_observation_status"] != receiving["status"] or
                    change["physical_transition_verified"] or
                    change["complete_board_verified"] or
                    change["simulation_ready"] or
                    before.get("complete_board_verified", False) or
                    before.get("simulation_ready", False)):
                raise ValueError("Left transition lineage or physical-state flag differs")
            row["pre_candidate_receiving_view_observation"] = {
                "view": "left", "status": before["status"],
                "sample_times_s": before["sample_times_s"],
                "coordinate_frame": "full_source_left_camera_pixels_not_metric",
                "stable_cap_proposals": before["stable_cap_proposals"],
                "complete_board_verified": False,
                "simulation_ready": False,
            }
            row["receiving_view_partial_cap_transition"] = change
        elif receiving is not None and receiving["view"] == "right":
            row["pre_candidate_receiving_view_observation"] = row.get(
                "pre_candidate_partial_cap_observation")
            row["receiving_view_partial_cap_transition"] = row.get(
                "partial_cap_image_transition")
        else:
            row["pre_candidate_receiving_view_observation"] = None
            row["receiving_view_partial_cap_transition"] = None
        if row.get("game_state_after") and (
                row["game_state_after"]["complete_board"] is not None or
                row["game_state_after"]["simulation_ready"]):
            raise ValueError("Partial cap transition cannot promote game state")
    result["status"] = "candidate_sequence_with_conditional_receiving_view_image_transitions"
    result["left_receiving_transition_status_counts"] = dict(Counter(
        row["comparison_status"] for row in delta["rows"]))
    result["complete_throw_sequence_verified"] = False
    return result
