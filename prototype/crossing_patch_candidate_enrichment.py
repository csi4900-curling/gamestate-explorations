"""Attach graded crossing-patch evidence without changing event decisions."""

from copy import deepcopy


def source_category(pixel_class):
    if pixel_class.startswith("stone_body") or pixel_class.startswith("yellow_cap_and_stone_body"):
        return "stone_shaped_pixels"
    if pixel_class.startswith("person"):
        return "person_pixels"
    if pixel_class.startswith("ambiguous"):
        return "ambiguous_pixels"
    raise ValueError(f"Unsupported reviewed pixel class: {pixel_class}")


def enrich_full_match_candidates(union, scores, packet, postscore_source_audit=None):
    output = deepcopy(union)
    by_id = {row["candidate_id"]: row for row in output["ordered_candidates"]}
    if len(by_id) != output["candidate_count"] or not all(
        row["physical_throw_verified"] is False
        and row["game_state_after"]["simulation_ready"] is False
        for row in by_id.values()
    ):
        raise ValueError("Input candidate inventory or physical-state claims differ")
    source = next(
        (item for item in packet["sources"] if item["source_id"] == union["source_id"]), None
    )
    if (
        source is None
        or not source["same_video_bytes_as_timeline"]
        or source["video_sha256"] != union["source_sha256"]
    ):
        raise ValueError("Patch packet Latvia source differs from full-match union")
    packet_by_key = {(row["source_id"], row["event_id"]): row for row in packet["rows"]}
    score_keys = [(row["source_id"], row["event_id"]) for row in scores["rows"]]
    if (
        len(packet_by_key) != len(packet["rows"])
        or len(score_keys) != len(set(score_keys))
        or set(score_keys) != set(packet_by_key)
    ):
        raise ValueError("Patch score and packet inventories differ")
    attached = []
    for score in scores["rows"]:
        key = (score["source_id"], score["event_id"])
        packet_row = packet_by_key.get(key)
        score_class = score.get("source_pixel_class", score.get("source_review"))
        model_positive = score.get("model_positive", score.get("predicted_stone_like"))
        if (
            packet_row is None
            or packet_row["source_review"] != score_class
            or len(score["sample_scores"]) != packet["samples_per_event"]
            or model_positive != (score["mean_score"] >= scores["threshold"])
        ):
            raise ValueError("Patch score and source packet differ")
        if score["source_id"] != union["source_id"]:
            continue
        candidate_id = "left:" + score["event_id"]
        candidate = by_id.get(candidate_id)
        if (
            candidate is None
            or candidate["observation_kind"] != "left_provisional_passage"
            or abs(candidate["source_time_s"] - packet_row["timeline_crossing_time_s"]) > 0.001
            or (score_class == "unreviewed" and candidate["source_pixel_review"] is not None)
            or (
                score_class != "unreviewed"
                and (
                    candidate["source_pixel_review"] is None
                    or source_category(candidate["source_pixel_review"]["source_pixel_class"])
                    != score_class
                )
            )
        ):
            raise ValueError(f"Patch score cannot join reviewed candidate: {candidate_id}")
        candidate["crossing_patch_appearance"] = {
            "model_sha256": scores["model_sha256"],
            "sample_scores": deepcopy(score["sample_scores"]),
            "mean_score": score["mean_score"],
            "model_positive": model_positive,
            "source_review_status": score_class,
            "evidence_role": "graded_object_appearance_not_event_decision",
        }
        attached.append(candidate_id)
    expected = sum(row["source_id"] == union["source_id"] for row in scores["rows"])
    if len(attached) != len(set(attached)) or len(attached) != expected or not attached:
        raise ValueError("Latvia patch score inventory differs")
    output["status"] = "full_match_candidate_union_with_graded_patch_evidence_not_throw_truth"
    output["crossing_patch_scored_left_count"] = len(attached)
    output["crossing_patch_scored_left_ids"] = sorted(attached)
    if postscore_source_audit is not None:
        if (
            postscore_source_audit["source_video_sha256"] != union["source_sha256"]
            or not postscore_source_audit["rows"]
        ):
            raise ValueError("Postscore source review inventory differs")
        reviewed_ids = set()
        for review in postscore_source_audit["rows"]:
            candidate_id = "left:" + review["candidate_id"]
            candidate = by_id.get(candidate_id)
            if (
                candidate is None
                or candidate_id in reviewed_ids
                or "crossing_patch_appearance" not in candidate
                or abs(
                    candidate["crossing_patch_appearance"]["mean_score"]
                    - review["frozen_patch_mean_score"]
                )
                > 0.000001
                or candidate["crossing_patch_appearance"]["model_positive"] is not False
                or review["physical_throw_verified"] is not False
            ):
                raise ValueError(f"Postscore source review cannot join: {candidate_id}")
            review_category = source_category(review["source_pixel_class"])
            prior = candidate["source_pixel_review"]
            if (
                prior is None
                and candidate["crossing_patch_appearance"]["source_review_status"] != "unreviewed"
            ) or (
                prior is not None
                and source_category(prior["source_pixel_class"]) != review_category
            ):
                raise ValueError(f"Postscore source class conflicts: {candidate_id}")
            image_name = review.get("review_page", postscore_source_audit.get("image"))
            if not image_name:
                raise ValueError("Postscore review image missing")
            review_record = {
                "source_pixel_class": review["source_pixel_class"],
                "review_origin": review["class_origin"],
                "image_path": (
                    "all-negative-patch-source-audit/"
                    if "review_page" in review
                    else "lowest-five-patch-source-audit/"
                )
                + image_name,
                "physical_throw_verified": False,
            }
            candidate["postscore_source_review"] = deepcopy(review_record)
            if prior is None:
                candidate["source_pixel_review"] = deepcopy(review_record)
                candidate["crossing_patch_appearance"]["source_review_added_after_scoring"] = True
            candidate["crossing_patch_appearance"]["postscore_source_review_attached"] = True
            reviewed_ids.add(candidate_id)
        output["postscore_source_reviewed_left_count"] = len(reviewed_ids)
        output["limitations"].append(
            "Model-negative paths were source-reviewed after patch scoring; that selected review cannot calibrate model accuracy."
        )
    output["limitations"].append(
        "Frozen patch scores rank source-reviewed object appearance; they do not accept, reject, or verify a physical throw."
    )
    return output
