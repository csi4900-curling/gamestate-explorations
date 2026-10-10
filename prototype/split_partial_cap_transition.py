"""Conservative image-coordinate changes between partial cap observations."""

from math import dist, isfinite


def compare_cap_sets(before, after, *, max_distance_px=5):
    if not isfinite(max_distance_px) or max_distance_px <= 0:
        raise ValueError("Invalid match radius")
    candidates = []
    for i, old in enumerate(before):
        for j, new in enumerate(after):
            if old["colour"] != new["colour"]:
                continue
            distance = dist(old["pixel_center"], new["pixel_center"])
            if distance <= max_distance_px:
                candidates.append((i, j, distance))
    before_degree = [sum(i == a for a, _, _ in candidates)
                     for i in range(len(before))]
    after_degree = [sum(j == b for _, b, _ in candidates)
                    for j in range(len(after))]
    unique = [(i, j, distance) for i, j, distance in candidates
              if before_degree[i] == after_degree[j] == 1]
    matched_before = {i for i, _, _ in unique}
    matched_after = {j for _, j, _ in unique}
    return {
        "locally_retained": [{
            "before_local_id": before[i]["local_observation_id"],
            "after_local_id": after[j]["local_observation_id"],
            "colour": before[i]["colour"],
            "pixel_shift": round(distance, 3),
        } for i, j, distance in unique],
        "no_longer_observed": [before[i]["local_observation_id"]
                               for i in range(len(before)) if before_degree[i] == 0],
        "newly_observed": [after[j]["local_observation_id"]
                           for j in range(len(after)) if after_degree[j] == 0],
        "unresolved_before": [before[i]["local_observation_id"]
                              for i in range(len(before))
                              if before_degree[i] > 0 and i not in matched_before],
        "unresolved_after": [after[j]["local_observation_id"]
                             for j in range(len(after))
                             if after_degree[j] > 0 and j not in matched_after],
        "physical_transition_verified": False,
        "simulation_ready": False,
    }


def compare_observation_rows(before, after, cross_scene_mae,
                             *, max_scene_mae=20, max_distance_px=5):
    if before["candidate_id"] != after["candidate_id"]:
        raise ValueError("Candidate IDs differ")
    if before["coordinate_frame"] != after["coordinate_frame"]:
        raise ValueError("Coordinate frames differ")
    status_before = before["observation_status"]
    status_after = after["observation_status"]
    if status_before.startswith("abstain_") or status_after.startswith("abstain_"):
        status = "abstain_pre_or_post_window"
        delta = None
    else:
        if cross_scene_mae is None or not isfinite(cross_scene_mae) or cross_scene_mae < 0:
            raise ValueError("Invalid cross-window scene difference")
        if cross_scene_mae >= max_scene_mae:
            status = "abstain_cross_window_scene_change"
            delta = None
        else:
            status = "partial_cap_image_comparison"
            delta = compare_cap_sets(before["stable_cap_proposals"],
                                     after["stable_cap_proposals"],
                                     max_distance_px=max_distance_px)
    return {
        "candidate_id": before["candidate_id"],
        "pre_observation_status": status_before,
        "post_observation_status": status_after,
        "cross_window_scene_mae": round(cross_scene_mae, 3)
        if cross_scene_mae is not None else None,
        "comparison_status": status,
        "image_cap_delta": delta,
        "physical_transition_verified": False,
        "complete_board_verified": False,
        "simulation_ready": False,
    }
