"""Conservative local matching between two video-derived partial boards."""

from math import dist, isfinite


def _position(stone):
    return (float(stone["canonical_lateral_house_radii"]),
            float(stone["longitudinal_house_radii"]))


def compare_partial_boards(before, after, *, max_distance_house_radii=0.10):
    """Match unambiguous same-colour observations without claiming stone IDs.

    Unmatched observations are additions/losses *from the visible partial
    boards*, not proven physical stone additions/removals.
    """
    if before["counter_anchor_s"] >= after["counter_anchor_s"]:
        raise ValueError("Counter anchors must advance")
    if not isfinite(max_distance_house_radii) or max_distance_house_radii <= 0:
        raise ValueError("Invalid match distance")
    first, second = before["stable_partial_board"], after["stable_partial_board"]
    candidates = []
    for i, old in enumerate(first):
        for j, new in enumerate(second):
            if old["colour"] != new["colour"]:
                continue
            distance = dist(_position(old), _position(new))
            if distance <= max_distance_house_radii:
                candidates.append((i, j, distance))
    old_degree = [sum(i == row[0] for row in candidates) for i in range(len(first))]
    new_degree = [sum(j == row[1] for row in candidates) for j in range(len(second))]
    unique = [(i, j, distance) for i, j, distance in candidates
              if old_degree[i] == new_degree[j] == 1]
    old_matched = {i for i, _, _ in unique}
    new_matched = {j for _, j, _ in unique}
    return {
        "before_shot_id": before["shot_id"],
        "after_shot_id": after["shot_id"],
        "counter_interval_s": [before["counter_anchor_s"], after["counter_anchor_s"]],
        "match_distance_house_radii": max_distance_house_radii,
        "locally_retained": [{
            "before_local_id": f"V{i + 1:02d}",
            "after_local_id": f"V{j + 1:02d}",
            "colour": first[i]["colour"],
            "position_shift_house_radii": round(distance, 4),
            "identity_status": "same_colour_nearby_observation_not_physical_identity",
        } for i, j, distance in unique],
        "no_longer_observed": [f"V{i + 1:02d}" for i in range(len(first))
                               if old_degree[i] == 0],
        "newly_observed": [f"V{j + 1:02d}" for j in range(len(second))
                           if new_degree[j] == 0],
        "unresolved_before": [f"V{i + 1:02d}" for i in range(len(first))
                              if old_degree[i] > 0 and i not in old_matched],
        "unresolved_after": [f"V{j + 1:02d}" for j in range(len(second))
                             if new_degree[j] > 0 and j not in new_matched],
        "physical_transition_verified": False,
        "simulation_ready": False,
    }
