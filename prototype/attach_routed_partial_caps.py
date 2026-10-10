"""Add conditional receiving-view image caps to full-match candidate rows."""

from collections import Counter
from copy import deepcopy


def attach_routed_partial_caps(sequence, routes, left_scan):
    source = sequence["source_sha256"]
    if routes["source_sha256"] != source or left_scan["source_sha256"] != source:
        raise ValueError("Source fingerprints differ")
    left_rows = {row["candidate_id"]: row for row in sequence["rows"]
                 if row["observation_kind"] == "left_tracked_passage"}
    route_by_id = {row["candidate_id"]: row for row in routes["rows"]}
    cap_by_id = {row["candidate_id"]: row for row in left_scan["rows"]}
    if (len(left_rows) != sequence["left_candidate_count"] or
            len(route_by_id) != len(routes["rows"]) or
            set(route_by_id) != set(left_rows) or
            len(cap_by_id) != len(left_scan["rows"]) or
            set(cap_by_id) != {key for key, row in route_by_id.items()
                               if row["conditional_receiving_view"] == "left"}):
        raise ValueError("Routed scan coverage differs from left candidate set")
    result = deepcopy(sequence)
    for row in result["rows"]:
        if row["candidate_id"] not in route_by_id:
            row["post_candidate_receiving_view_observation"] = None
            continue
        route = route_by_id[row["candidate_id"]]
        view = route["conditional_receiving_view"]
        if (route["observation_time_s"] != row["observation_time_s"] or
                route["colour_claim"] != row["colour_claim"]):
            raise ValueError("Routed candidate identity changed")
        if view == "left":
            scan = cap_by_id[row["candidate_id"]]
            if (scan.get("simulation_ready") or
                    scan.get("complete_board_verified") or
                    scan.get("physical_settle_verified")):
                raise ValueError("Left image caps cannot promote physical state")
            observation = {
                "view": "left", "routing_status": route["routing_status"],
                "status": scan["status"],
                "sample_times_s": scan["sample_times_s"],
                "coordinate_frame": "full_source_left_camera_pixels_not_metric",
                "stable_cap_proposals": scan["stable_cap_proposals"],
                "camera_registration_verified": False,
                "complete_board_verified": False,
                "physical_settle_verified": False,
                "delivered_stone_identity_verified": False,
                "simulation_ready": False,
            }
            relevance = "prior_right_scan_not_receiving_view_conditional"
        elif view == "right":
            prior = row.get("post_candidate_partial_cap_observation")
            if prior is None:
                raise ValueError("Routed right view has no prior right scan")
            if (prior["complete_board_verified"] or prior["physical_settle_verified"]
                    or prior["simulation_ready"]):
                raise ValueError("Right image caps cannot promote physical state")
            observation = {
                "view": "right", "routing_status": route["routing_status"],
                "status": prior["status"],
                "sample_times_s": prior["sample_times_s"],
                "coordinate_frame": prior["coordinate_frame"],
                "stable_cap_proposals": prior["stable_cap_proposals"],
                "camera_registration_verified": False,
                "complete_board_verified": False,
                "physical_settle_verified": False,
                "delivered_stone_identity_verified": False,
                "simulation_ready": False,
            }
            relevance = "prior_right_scan_receiving_view_conditional"
        else:
            observation = None
            relevance = "receiving_view_unknown"
        row["post_candidate_receiving_view_observation"] = observation
        row["prior_right_scan_view_relevance"] = relevance
        if (row["game_state_after"]["complete_board"] is not None or
                row["game_state_after"]["simulation_ready"]):
            raise ValueError("Candidate sequence claims physical board state")
    result["status"] = "candidate_sequence_with_conditional_receiving_view_partial_caps"
    result["receiving_view_status_counts"] = dict(Counter(
        (row["post_candidate_receiving_view_observation"] or {}).get("status", "none")
        for row in result["rows"] if row["candidate_id"] in route_by_id))
    result["receiving_view_counts"] = routes["conditional_receiving_view_counts"]
    result["complete_throw_sequence_verified"] = False
    return result
