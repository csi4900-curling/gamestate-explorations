"""Guarded image-only changes between adjacent right-entry board samples."""

from right_view_cap_sequence import compare_cap_sets


USABLE = "partial_stable_colour_cap_proposals"


def build_right_board_sequence(union, boards, alignments, *, min_blue_iou=0.7):
    if union["source_sha256"] != boards["source_sha256"]:
        raise ValueError("Candidate and board sources differ")
    rows = boards["rows"]
    ids = [row["right_entry_id"] for row in rows]
    if len(ids) != len(set(ids)) or any(
        a["entry_time_s"] >= b["entry_time_s"] for a, b in zip(rows, rows[1:])
    ):
        raise ValueError("Board entries must be uniquely identified and ordered")
    if len(alignments) != max(0, len(rows) - 1):
        raise ValueError("Alignment must cover every adjacent right-entry pair")
    candidates = union["candidates"]
    if len({row["candidate_id"] for row in candidates}) != len(candidates):
        raise ValueError("Duplicate candidate ID")
    right_by_id = {
        row["right_entry_ids"][0]: row
        for row in candidates
        if row["origin"] == "right_entry_review"
    }
    if set(right_by_id) != set(ids):
        raise ValueError("Right-entry candidates and board entries differ")
    transitions = []
    for before, after, alignment in zip(rows, rows[1:], alignments):
        first, second = before["right_entry_id"], after["right_entry_id"]
        if (
            alignment["before_right_entry_id"] != first
            or alignment["after_right_entry_id"] != second
        ):
            raise ValueError("Alignment and board pair differ")
        interval = [before["entry_time_s"], after["entry_time_s"]]
        intervening = [
            row["candidate_id"]
            for row in candidates
            if interval[0] < row["source_time_s"] < interval[1]
            and row["candidate_id"] != right_by_id[second]["candidate_id"]
        ]
        item = {
            "before_right_entry_id": first,
            "after_right_entry_id": second,
            "entry_interval_s": interval,
            "intervening_candidate_ids": intervening,
            "same_physical_end_verified": False,
            "physical_stone_identity_verified": False,
            "physical_board_transition_verified": False,
            "simulation_ready": False,
        }
        if first.split(":", 1)[0] != second.split(":", 1)[0]:
            item["status"] = "abstain_route_interval_change"
        elif intervening:
            item["status"] = "abstain_intervening_candidate"
        elif before["observation_status"] != USABLE or after["observation_status"] != USABLE:
            item["status"] = "abstain_missing_usable_cap_set"
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
                compare_cap_sets(before["stable_cap_proposals"], after["stable_cap_proposals"])
            )
        transitions.append(item)
    return {
        "status": "adjacent_partial_image_cap_changes_not_physical_game_state",
        "source_sha256": union["source_sha256"],
        "transition_count": len(transitions),
        "transitions": transitions,
        "limitations": [
            "Only adjacent right-entry samples are compared; other candidates force abstention.",
            "A sampled painted-ring alignment does not prove constant camera pose or same physical end.",
            "Matched caps are local image observations, not persistent stone identities.",
            "New or lost caps do not prove a delivered, removed, or displaced stone.",
        ],
    }
