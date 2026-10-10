"""Attach postscore positive-tier pixel reviews to a full-match evidence ledger."""

from collections import Counter
from copy import deepcopy

from .crossing_patch_candidate_enrichment import source_category


def attach_positive_source_reviews(negative_ledger, positive_audit):
    output = deepcopy(negative_ledger)
    if (
        positive_audit["source_video_sha256"] != output["source_sha256"]
        or output["crossing_patch_scored_left_count"] != 72
        or output["postscore_source_reviewed_left_count"] != 34
        or len(positive_audit["rows"]) != 38
    ):
        raise ValueError("Positive review and scored full-match inventory differ")
    by_id = {row["candidate_id"]: row for row in output["ordered_candidates"]}
    if len(by_id) != output["candidate_count"]:
        raise ValueError("Full-match candidate IDs are not unique")
    attached = set()
    for review in positive_audit["rows"]:
        candidate_id = "left:" + review["candidate_id"]
        candidate = by_id.get(candidate_id)
        if (
            candidate is None
            or candidate_id in attached
            or candidate["observation_kind"] != "left_provisional_passage"
            or "postscore_source_review" in candidate
            or candidate["crossing_patch_appearance"]["model_positive"] is not True
            or abs(
                candidate["crossing_patch_appearance"]["mean_score"]
                - review["frozen_patch_mean_score"]
            )
            > 0.000001
            or review["source_pixel_class"] != "stone_body_pixels_in_crossing_crops"
            or review["physical_throw_verified"] is not False
        ):
            raise ValueError(f"Positive source review cannot join: {candidate_id}")
        prior = candidate["source_pixel_review"]
        if (
            prior is not None
            and source_category(prior["source_pixel_class"]) != "stone_shaped_pixels"
        ):
            raise ValueError(f"Positive source class conflicts: {candidate_id}")
        record = {
            "source_pixel_class": review["source_pixel_class"],
            "review_origin": review["class_origin"],
            "image_path": "all-positive-patch-source-audit/" + review["review_page"],
            "physical_throw_verified": False,
        }
        candidate["postscore_source_review"] = deepcopy(record)
        candidate["crossing_patch_appearance"]["postscore_source_review_attached"] = True
        if prior is None:
            candidate["source_pixel_review"] = deepcopy(record)
            candidate["crossing_patch_appearance"]["source_review_added_after_scoring"] = True
        attached.add(candidate_id)
    accepted = [
        row
        for row in output["ordered_candidates"]
        if row["observation_kind"] == "left_provisional_passage"
    ]
    if len(accepted) != 72 or any(row["source_pixel_review"] is None for row in accepted):
        raise ValueError("Accepted left source-pixel review coverage incomplete")
    counts = Counter(
        source_category(row["source_pixel_review"]["source_pixel_class"]) for row in accepted
    )
    if counts != {"stone_shaped_pixels": 70, "person_pixels": 1, "ambiguous_pixels": 1}:
        raise ValueError("Accepted left source-pixel class counts differ")
    if any(
        row["physical_throw_verified"] is not False
        or row["game_state_after"]["simulation_ready"] is not False
        for row in output["ordered_candidates"]
    ):
        raise ValueError("Physical event or game-state claim changed")
    output["status"] = (
        "full_match_candidate_union_all_accepted_left_source_pixels_reviewed_not_throw_truth"
    )
    output["positive_postscore_source_reviewed_left_count"] = len(attached)
    output["source_pixel_reviewed_accepted_left_count"] = len(accepted)
    output["accepted_left_source_pixel_class_counts"] = dict(counts)
    output["limitations"].append(
        "All 72 accepted left crossings have same-agent source-pixel classes, but these do not certify distinct physical throws or complete-match recall."
    )
    return output
