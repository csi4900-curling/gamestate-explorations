"""Attach all withheld crossing source-pixel reviews without promoting events."""

from collections import Counter
from copy import deepcopy


def attach_withheld_source_reviews(accepted_ledger, withheld_audit):
    output = deepcopy(accepted_ledger)
    if (withheld_audit["source_video_sha256"] != output["source_sha256"] or
            len(withheld_audit["rows"]) != 47 or
            output["candidate_count"] != 147 or
            output["source_pixel_reviewed_accepted_left_count"] != 72):
        raise ValueError("Withheld review and full-match inventory differ")
    by_id = {row["candidate_id"]: row for row in output["ordered_candidates"]}
    if len(by_id) != output["candidate_count"]:
        raise ValueError("Full-match candidate IDs are not unique")
    attached = set()
    for review in withheld_audit["rows"]:
        candidate_id = "left:" + review["candidate_id"]
        candidate = by_id.get(candidate_id)
        if (candidate is None or candidate_id in attached or
                candidate["observation_kind"] != "left_unconfirmed_raw_motion" or
                "postscore_source_review" in candidate or
                review["physical_throw_verified"] is not False or
                review["source_pixel_class"] not in (
                    "person_or_equipment_pixels_in_crossing_crops",
                    "ambiguous_low_red_pixels_near_wheelchair")):
            raise ValueError(f"Withheld source review cannot join: {candidate_id}")
        prior = candidate["source_pixel_review"]
        if prior is not None:
            old = prior["source_pixel_class"]
            if (old.startswith("person") and review["source_pixel_class"].startswith("ambiguous")) or (
                    old.startswith("ambiguous") and review["source_pixel_class"].startswith("person")):
                raise ValueError(f"Prior withheld source class conflicts: {candidate_id}")
        record = {
            "source_pixel_class": review["source_pixel_class"],
            "review_origin": review["class_origin"],
            "image_path": "withheld-left-crossing-patch-source-audit/" + review["review_page"],
            "physical_throw_verified": False,
        }
        candidate["postscore_source_review"] = deepcopy(record)
        if prior is None:
            candidate["source_pixel_review"] = deepcopy(record)
        attached.add(candidate_id)
    withheld = [row for row in output["ordered_candidates"] if row[
        "observation_kind"] == "left_unconfirmed_raw_motion"]
    if len(withheld) != 47 or len(attached) != 47 or any(
            row["source_pixel_review"] is None for row in withheld):
        raise ValueError("Withheld left review coverage incomplete")
    counts = Counter(row["postscore_source_review"]["source_pixel_class"]
                     for row in withheld)
    if counts != {"person_or_equipment_pixels_in_crossing_crops": 45,
                  "ambiguous_low_red_pixels_near_wheelchair": 2}:
        raise ValueError("Unexpected withheld pixel class counts")
    if any(row["physical_throw_verified"] is not False or
           row["game_state_after"]["simulation_ready"] is not False
           for row in output["ordered_candidates"]):
        raise ValueError("Physical event or game-state claim changed")
    output["status"] = "full_match_candidate_union_all_left_crossing_pixels_reviewed_not_throw_truth"
    output["source_pixel_reviewed_withheld_left_count"] = 47
    output["withheld_left_source_pixel_class_counts"] = dict(counts)
    output["limitations"].append(
        "All 47 withheld left tracks have same-agent crossing-patch classes; this does not establish complete-match throw recall, since stones outside these tracked crops or camera coverage remain possible.")
    return output
