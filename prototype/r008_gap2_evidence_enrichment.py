"""Attach the R008 source-pixel and association diagnostic to the ledger."""

from copy import deepcopy


def attach_r008_gap2_evidence(ledger, audit):
    output = deepcopy(ledger)
    if (
        ledger["source_sha256"] != audit["source_video_sha256"]
        or ledger["candidate_count"] != 152
        or ledger["development_possible_event_review_count"] != 98
        or ledger["older_right_only_without_full_area_match"] != ["right:R008"]
        or audit["candidate_id"] != "right:R008"
        or audit["source_pixel_class"] != "moving_red_stone_body_pixels"
        or audit["physical_throw_verified"] is not False
        or audit["old_prefix_equals_combined_split_raw_points"] is not True
        or set(audit["local_gap2_recoveries"]) != {"area_gap2", "global_gap2"}
    ):
        raise ValueError("R008 source review and full-match ledger differ")
    rows = [row for row in output["ordered_candidates"] if row["candidate_id"] == "right:R008"]
    if len(rows) != 1:
        raise ValueError("R008 is not a unique candidate")
    row = rows[0]
    if (
        row["observation_kind"] != "right_only_review_entry"
        or row["source_pixel_review"] is not None
        or row["physical_throw_verified"] is not False
        or row["game_state_after"]["simulation_ready"] is not False
        or row["observed_motion"]["observed_prefix_interval_s"] != audit["old_prefix_interval_s"]
    ):
        raise ValueError("R008 prior evidence differs")
    row["source_pixel_review"] = {
        "source_pixel_class": audit["source_pixel_class"],
        "review_origin": audit["source_class_origin"],
        "image_path": audit["archived_source_sheet_path"],
        "physical_throw_verified": False,
    }
    row["right_area_association_diagnostic"] = {
        "one_second_gap_raw_track_ids": audit["one_second_gap_area_raw_track_ids"],
        "old_prefix_equals_combined_split_raw_points": True,
        "local_gap2_recoveries": deepcopy(audit["local_gap2_recoveries"]),
        "physical_stone_identity_verified": False,
    }
    output["status"] = "full_match_union_with_r008_source_pixel_and_gap2_diagnostic_not_throw_truth"
    output["limitations"].append(
        "The unmatched old right entry R008 has source-reviewed stone-body pixels and exact local gap-two reassociation; neither certifies its physical delivery or full-source detector recall."
    )
    if (
        output["candidate_count"] != 152
        or output["development_possible_event_review_count"] != 98
        or output["physical_throw_count_verified"] is not None
        or any(
            item["physical_throw_verified"] is not False
            or item["game_state_after"]["simulation_ready"] is not False
            for item in output["ordered_candidates"]
        )
    ):
        raise ValueError("R008 enrichment changed event/state claims")
    return output
