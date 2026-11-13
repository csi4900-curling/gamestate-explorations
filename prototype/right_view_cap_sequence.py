"""Conservative image-pixel associations between adjacent partial cap sets."""

from math import dist, isfinite


def compare_cap_sets(before, after, *, max_distance_px=5.0):
    if not isfinite(max_distance_px) or max_distance_px <= 0:
        raise ValueError("Invalid maximum pixel separation")
    neighbors_before = [[] for _ in before]
    neighbors_after = [[] for _ in after]
    for i, old in enumerate(before):
        for j, new in enumerate(after):
            if old["colour"] != new["colour"]:
                continue
            separation = dist(old["pixel_center"], new["pixel_center"])
            if separation <= max_distance_px:
                neighbors_before[i].append((j, separation))
                neighbors_after[j].append((i, separation))
    matches = []
    for i, options in enumerate(neighbors_before):
        if len(options) != 1:
            continue
        j, separation = options[0]
        if len(neighbors_after[j]) != 1:
            continue
        matches.append(
            {
                "before_local_cap_id": before[i]["local_observation_id"],
                "after_local_cap_id": after[j]["local_observation_id"],
                "colour": before[i]["colour"],
                "image_position_shift_px": round(separation, 2),
                "physical_stone_identity_verified": False,
            }
        )
    matched_before = {row["before_local_cap_id"] for row in matches}
    matched_after = {row["after_local_cap_id"] for row in matches}
    return {
        "matched_local_caps": matches,
        "before_only_local_cap_ids": [
            row["local_observation_id"] for i, row in enumerate(before) if not neighbors_before[i]
        ],
        "after_only_local_cap_ids": [
            row["local_observation_id"] for j, row in enumerate(after) if not neighbors_after[j]
        ],
        "ambiguous_before_local_cap_ids": [
            row["local_observation_id"]
            for i, row in enumerate(before)
            if neighbors_before[i] and row["local_observation_id"] not in matched_before
        ],
        "ambiguous_after_local_cap_ids": [
            row["local_observation_id"]
            for j, row in enumerate(after)
            if neighbors_after[j] and row["local_observation_id"] not in matched_after
        ],
    }


def adjacent_cap_sequence(rows, alignment_pairs, *, min_blue_mask_iou=0.7):
    if any(a["entry_time_s"] >= b["entry_time_s"] for a, b in zip(rows, rows[1:])):
        raise ValueError("Entries must advance in source time")
    if not 0 < min_blue_mask_iou <= 1:
        raise ValueError("Invalid painted-house overlap threshold")
    if len(alignment_pairs) != max(0, len(rows) - 1):
        raise ValueError("Alignment rows must cover every adjacent pair")
    transitions = []
    for before, after, alignment in zip(rows, rows[1:], alignment_pairs):
        if (
            alignment["before_right_track_id"] != before["right_raw_track_id"]
            or alignment["after_right_track_id"] != after["right_raw_track_id"]
        ):
            raise ValueError("Alignment and cap sequence order differ")
        transition = {
            "before_right_track_id": before["right_raw_track_id"],
            "after_right_track_id": after["right_raw_track_id"],
            "entry_interval_s": [before["entry_time_s"], after["entry_time_s"]],
            "before_observation_status": before["observation_status"],
            "after_observation_status": after["observation_status"],
            "same_camera_pose_verified": False,
            "sampled_house_alignment_supported": False,
            "same_physical_end_verified": False,
            "physical_addition_removal_or_collision_inferred": False,
            "simulation_ready": False,
        }
        if (
            before["observation_status"] != "partial_stable_colour_cap_proposals"
            or after["observation_status"] != "partial_stable_colour_cap_proposals"
        ):
            transition["status"] = "abstain_missing_usable_cap_set"
        elif (
            alignment["status"] != "painted_ring_alignment_probe"
            or not alignment["zero_translation_is_best"]
            or alignment["best_translation_second_to_first_px"] != [0, 0]
            or alignment["best_mask_iou"] < min_blue_mask_iou
        ):
            transition["status"] = "abstain_house_image_alignment"
        else:
            transition["status"] = "conditional_image_pixel_cap_association"
            transition["sampled_house_alignment_supported"] = True
            transition["sampled_house_blue_mask_iou"] = alignment["best_mask_iou"]
            transition.update(
                compare_cap_sets(before["stable_cap_proposals"], after["stable_cap_proposals"])
            )
        transitions.append(transition)
    return transitions
