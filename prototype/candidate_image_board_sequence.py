"""Adjacent candidate image-board comparisons with explicit abstentions."""

from collections import Counter

from right_view_cap_sequence import compare_cap_sets


USABLE = "partial_stable_colour_cap_proposals"


def compare_candidate_boards(handoff, alignments, *, min_blue_iou=0.7):
    rows = handoff["ordered_candidates"]
    if len({row["candidate_id"] for row in rows}) != len(rows):
        raise ValueError("Duplicate candidate ID")
    if any(a["source_time_s"] >= b["source_time_s"] for a, b in zip(rows, rows[1:])):
        raise ValueError("Candidate times must advance")
    if len(alignments) != max(0, len(rows) - 1):
        raise ValueError("Alignment must cover every adjacent candidate pair")
    transitions = []
    for before, after, alignment in zip(rows, rows[1:], alignments):
        a, b = before["candidate_id"], after["candidate_id"]
        if alignment["before_candidate_id"] != a or alignment["after_candidate_id"] != b:
            raise ValueError("Alignment and candidate pair differ")
        first = before["post_candidate_image_observation"]
        second = after["post_candidate_image_observation"]
        item = {
            "before_candidate_id": a,
            "after_candidate_id": b,
            "candidate_interval_s": [before["source_time_s"], after["source_time_s"]],
            "before_observation_status": first["status"],
            "after_observation_status": second["status"],
            "same_physical_end_verified": False,
            "physical_stone_identity_verified": False,
            "physical_board_transition_verified": False,
            "simulation_ready": False,
        }
        if first["status"] != USABLE or second["status"] != USABLE:
            item["status"] = "abstain_missing_usable_cap_set"
        elif before["origin"] != after["origin"]:
            item["status"] = "abstain_origin_change"
        elif (
            before["origin"] == "left_routed_proposal"
            and before["source_run_id"] != after["source_run_id"]
        ):
            item["status"] = "abstain_route_run_change"
        elif (
            before["origin"] == "right_entry_review"
            and before["right_entry_ids"][0].split(":", 1)[0]
            != after["right_entry_ids"][0].split(":", 1)[0]
        ):
            item["status"] = "abstain_route_interval_change"
        elif (
            not first["sample_times_s"]
            or not second["sample_times_s"]
            or first["sample_times_s"][-1] >= after["source_time_s"] - 1
            or first["sample_times_s"][-1] >= second["sample_times_s"][0]
        ):
            item["status"] = "abstain_overlapping_or_late_board_samples"
        elif (
            alignment["status"] != "painted_ring_alignment_probe"
            or not alignment["zero_translation_is_best"]
            or alignment["best_translation_second_to_first_px"] != [0, 0]
            or alignment["best_mask_iou"] < min_blue_iou
        ):
            item["status"] = "abstain_house_image_alignment"
        else:
            item["status"] = "conditional_image_pixel_cap_association"
            item["sampled_house_blue_mask_iou"] = alignment["best_mask_iou"]
            item.update(
                compare_cap_sets(first["stable_cap_proposals"], second["stable_cap_proposals"])
            )
        transitions.append(item)
    return {
        "status": "full_candidate_partial_image_board_sequence_not_game_state",
        "source_sha256": handoff["source_sha256"],
        "candidate_count": len(rows),
        "transition_count": len(transitions),
        "transition_status_counts": dict(Counter(row["status"] for row in transitions)),
        "transitions": transitions,
        "limitations": [
            "Candidate adjacency is not independently verified physical throw adjacency.",
            "A sampled painted-ring match does not prove same camera pose throughout a throw.",
            "Image caps are partial and can include nonstones or omit occluded stones.",
            "Matched caps are not persistent physical stone IDs or a complete game state.",
        ],
    }
