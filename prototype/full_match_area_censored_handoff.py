"""Add late right-camera source reviews to a full-match candidate ledger."""

from collections import Counter
from copy import deepcopy


def build_full_match_area_censored_handoff(
    legacy, censored, withheld_cross_view_audit, accepted_no_right_audit
):
    if legacy["source_sha256"] != censored["source_video_sha256"]["lowres"]:
        raise ValueError("Full-match and late source fingerprints differ")
    if not (
        legacy["source_interval_s"][0]
        <= censored["source_interval_s"][0]
        < censored["source_interval_s"][1]
        <= legacy["source_interval_s"][1]
    ):
        raise ValueError("Late source interval outside full match")
    blind = [row["interval_s"] for row in legacy["left_trigger_blind_intervals"]]
    original = deepcopy(legacy["ordered_candidates"])
    original_ids = {row["candidate_id"] for row in original}
    if (
        len(original) != legacy["candidate_count"]
        or len(original_ids) != len(original)
        or sum(
            row["observation_kind"] in ("left_provisional_passage", "right_only_review_entry")
            for row in original
        )
        != legacy["possible_event_proposal_count"]
    ):
        raise ValueError("Original candidate inventory differs")
    if withheld_cross_view_audit["source_video_sha256"] != legacy["source_sha256"]:
        raise ValueError("Withheld cross-view source fingerprint differs")
    if accepted_no_right_audit["source_video_sha256"] != legacy["source_sha256"]:
        raise ValueError("Accepted no-right source fingerprint differs")
    left_by_id = {
        row["candidate_id"].split("-")[-1]: row
        for row in original
        if row["observation_kind"] == "left_unconfirmed_raw_motion"
    }
    left_reviews = [
        row for row in withheld_cross_view_audit["marked_pixels"] if row["camera"] == "left"
    ]
    right_reviews = {
        row["candidate_id"]: row
        for row in withheld_cross_view_audit["marked_pixels"]
        if row["camera"] == "right"
    }
    if (
        len(left_reviews) != withheld_cross_view_audit["marked_left_count"]
        or len(right_reviews) != withheld_cross_view_audit["marked_right_count"]
        or len({row["candidate_id"] for row in left_reviews}) != len(left_reviews)
    ):
        raise ValueError("Withheld cross-view source review inventory differs")
    for review in left_reviews:
        candidate = left_by_id.get(review["candidate_id"])
        if (
            candidate is None
            or candidate["source_pixel_review"] is not None
            or abs(candidate["source_time_s"] - review["source_time_s"]) > 0.001
            or review["physical_throw_verified"] is not False
        ):
            raise ValueError("Withheld left source review differs")
        candidate["source_pixel_review"] = {
            "source_pixel_class": review["source_pixel_class"],
            "review_origin": "same_agent_postproposal_source_review",
            "image_path": "withheld-cross-view-source-audit/" + review["image"],
            "clearly_nonstone_at_marked_pixel": review["clearly_nonstone_at_marked_pixel"],
            "physical_throw_verified": False,
        }
    attached = set()
    for episode in withheld_cross_view_audit["episodes"]:
        for left_id in episode["left_candidate_ids"]:
            candidate = left_by_id.get(left_id)
            if candidate is None or left_id in attached or candidate["source_pixel_review"] is None:
                raise ValueError("Withheld cross-view episode link differs")
            right_ids = [rid.removeprefix("R01:") for rid in episode["right_proposal_ids"]]
            if any(rid not in right_reviews for rid in right_ids):
                raise ValueError("Right source review missing")
            candidate["withheld_cross_view_review"] = {
                "episode_id": episode["episode_id"],
                "right_proposal_ids": deepcopy(episode["right_proposal_ids"]),
                "right_pixel_classes": {
                    rid: right_reviews[rid.removeprefix("R01:")]["source_pixel_class"]
                    for rid in episode["right_proposal_ids"]
                },
                "source_review_result": episode["source_review_result"],
                "physical_throw_promotion": False,
            }
            attached.add(left_id)
    if attached != {row["candidate_id"] for row in left_reviews}:
        raise ValueError("Unattached withheld source review")
    accepted_by_id = {
        row["candidate_id"].split("-")[-1]: row
        for row in original
        if row["observation_kind"] == "left_provisional_passage"
    }
    no_right_reviews = accepted_no_right_audit["rows"]
    if len(no_right_reviews) != accepted_no_right_audit["accepted_left_without_right_count"] or len(
        {row["left_candidate_id"] for row in no_right_reviews}
    ) != len(no_right_reviews):
        raise ValueError("Accepted no-right review inventory differs")
    for review in no_right_reviews:
        candidate = accepted_by_id.get(review["left_candidate_id"])
        if (
            candidate is None
            or abs(candidate["source_time_s"] - review["source_time_s"]) > 0.001
            or candidate["colour_claim"] != review["colour_claim"]
            or review["right_time_colour_direction_candidate_count"] != 0
            or review["physical_throw_verified"] is not False
        ):
            raise ValueError("Accepted no-right source review differs")
        prior_review = candidate["source_pixel_review"]
        if prior_review is not None and not (
            prior_review["source_pixel_class"].startswith("person")
            and review["source_pixel_class"].startswith("person")
        ):
            raise ValueError("Accepted source reviews conflict")
        candidate["accepted_no_right_source_review"] = {
            "source_pixel_class": review["source_pixel_class"],
            "stone_shaped_pixels_at_crossing": review["stone_shaped_pixels_at_crossing"],
            "image_path": "accepted-no-right-source-audit/" + review["image"],
            "review_origin": "same_agent_postproposal_source_review",
            "physical_throw_verified": False,
        }
        if prior_review is None:
            candidate["source_pixel_review"] = deepcopy(
                candidate["accepted_no_right_source_review"]
            )
    new = censored["events"]
    late_ids = {row["right_proposal_id"] for row in new}
    if len(late_ids) != len(new) or len(new) != censored["candidate_count"]:
        raise ValueError("Late right candidate inventory differs")
    possible_times = [
        row["source_time_s"]
        for row in original
        if row["observation_kind"] in ("left_provisional_passage", "right_only_review_entry")
    ]
    additions = []
    for row in new:
        time_s = row["passage_time_s"]
        if (
            not any(a <= time_s < b for a, b in blind)
            or not censored["source_interval_s"][0] <= time_s < censored["source_interval_s"][1]
            or any(abs(time_s - prior) <= 2 for prior in possible_times)
        ):
            raise ValueError("Late right candidate outside blind interval or duplicated")
        stone_pixels = row["source_prefix_class"] == "moving_stone_pixels"
        if not stone_pixels and row["source_prefix_class"] != "person_or_clothing_pixels":
            raise ValueError("Unknown source pixel class")
        if (
            row["physical_throw_verified"] is not False
            or row["physical_settle_time_s"] is not None
            or row["simulation_ready"] is not False
        ):
            raise ValueError("Physical event claim in late candidate")
        additions.append(
            {
                "candidate_id": f"right_area:{row['right_proposal_id']}",
                "source_time_s": time_s,
                "time_semantics": "interpolated_right_image_line_crossing",
                "colour_claim": row["colour_claim"],
                "observation_kind": (
                    "right_area_reviewed_stone_pixels"
                    if stone_pixels
                    else "right_area_reviewed_person_pixels"
                ),
                "evidence_tier": (
                    "same_agent_short_stone_pixel_path_not_physical_throw"
                    if stone_pixels
                    else "same_agent_person_pixel_path_not_throw"
                ),
                "left_screen_reason": None,
                "left_coverage_status": "left_static_right_active",
                "observed_motion": deepcopy(row["observed_moving_pixels"]),
                "post_candidate_partial_board": deepcopy(row["following_partial_image_board"]),
                "terminal_visibility": deepcopy(row["terminal_visibility"]),
                "physical_throw_verified": False,
                "game_state_after": {
                    "end_identity": None,
                    "official_shot_identity": None,
                    "release_time_s": None,
                    "settle_time_s": None,
                    "complete_board": None,
                    "persistent_stone_ids": None,
                    "metric_trajectory": None,
                    "spin_revolution_count": None,
                    "simulation_ready": False,
                },
                "source_pixel_review": {
                    "source_pixel_class": row["source_prefix_class"],
                    "review_origin": "same_agent_prediction_targeted",
                    "physical_throw_verified": False,
                },
                "source_censored_handoff_id": row["right_proposal_id"],
                "sequence_id": None,
            }
        )
    merged = original + additions
    if len({row["candidate_id"] for row in merged}) != len(merged):
        raise ValueError("Merged candidate ID collision")
    merged.sort(key=lambda row: (row["source_time_s"], row["candidate_id"]))
    for index, row in enumerate(merged, 1):
        row["merged_order_index"] = index
    counts = Counter(row["observation_kind"] for row in merged)
    return {
        "status": "full_match_development_candidate_union_not_throw_truth",
        "source_id": legacy["source_id"],
        "source_sha256": legacy["source_sha256"],
        "source_interval_s": deepcopy(legacy["source_interval_s"]),
        "routed_coverage_gaps_s": deepcopy(legacy["routed_coverage_gaps_s"]),
        "left_trigger_blind_intervals": deepcopy(legacy["left_trigger_blind_intervals"]),
        "legacy_candidate_count": len(original),
        "late_right_area_candidate_count": len(additions),
        "source_reviewed_withheld_cross_view_count": len(attached),
        "source_reviewed_accepted_no_right_count": len(no_right_reviews),
        "candidate_count": len(merged),
        "candidate_counts_by_kind": dict(counts),
        "development_possible_event_review_count": (
            legacy["possible_event_proposal_count"] + counts["right_area_reviewed_stone_pixels"]
        ),
        "physical_throw_count_verified": None,
        "complete_throw_sequence_verified": False,
        "ordered_candidates": merged,
        "limitations": [
            "The possible-event review count is not a physical throw count or a measured recall result.",
            "One old screened left path is source-reviewed as player pixels; the other left candidates are not exhaustively verified.",
            "Late right stone/person source classes are same-agent prediction-targeted reviews, not independent event labels.",
            "Source-reviewed left/right timing matches do not rescue any withheld candidate; low red pixels near wheelchairs remain ambiguous.",
            "Eight accepted left passages without a right match have stone-shaped source pixels; a right match is not a safe hard acceptance requirement.",
            "All later boards are partial camera-local colour observations, not complete post-throw game states.",
        ],
    }
