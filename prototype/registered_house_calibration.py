"""Conservative donor selection for image-registered house calibration reuse."""


def calibration_group(candidate):
    if candidate["origin"] == "left_routed_proposal":
        return candidate["origin"], candidate["source_run_id"]
    if candidate["origin"] == "right_entry_review":
        return candidate["origin"], candidate["right_entry_ids"][0].split(":", 1)[0]
    raise ValueError("Unknown candidate origin")


def nearest_donor(target, accepted, candidates):
    group = calibration_group(candidates[target["candidate_id"]])
    matching = [
        row for row in accepted if calibration_group(candidates[row["candidate_id"]]) == group
    ]
    if not matching:
        return None
    return min(
        matching,
        key=lambda row: (
            abs(row["sample_times_s"][1] - target["sample_times_s"][1]),
            row["candidate_id"],
        ),
    )


def alignment_supported(alignment, *, min_blue_iou=0.7):
    return bool(
        alignment["zero_translation_is_best"]
        and alignment["best_translation_second_to_first_px"] == [0, 0]
        and alignment["best_mask_iou"] >= min_blue_iou
    )
