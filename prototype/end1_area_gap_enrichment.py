"""Add the source-reviewed A008 right path omitted from the left-led union."""

from collections import Counter
from copy import deepcopy


def attach_end1_area_gap_candidate(ledger, audit, scan):
    output = deepcopy(ledger)
    if (ledger["source_sha256"] != audit["source_video_sha256"] != scan[
            "source_sha256"] or ledger["candidate_count"] != 148 or
            ledger["development_possible_event_review_count"] != 97 or
            audit["candidate_id"] != "right_area:R01:A008" or
            audit["source_pixel_class"] != "moving_red_stone_body_pixels" or
            audit["physical_throw_verified"] is not False or
            audit["same_stone_identity_to_board_verified"] is not False):
        raise ValueError("A008 source review and candidate inventory differ")
    ids = {row["candidate_id"] for row in output["ordered_candidates"]}
    if len(ids) != 148 or audit["candidate_id"] in ids:
        raise ValueError("Original candidate IDs differ or A008 already exists")
    proposals = [row for row in scan["directional_review_proposals"]
                 if row["raw_track_id"] == audit["raw_track_id"]]
    tracks = [row for row in scan["raw_tracks"] if row["track_id"] == audit[
        "raw_track_id"]]
    if len(proposals) != 1 or len(tracks) != 1:
        raise ValueError("A008 raw path is not unique")
    proposal, track = proposals[0], tracks[0]
    if (proposal["passage"]["time_s"] != audit["source_time_s"] or
            proposal["passage_kind"] != audit["time_semantics"] or
            not proposal["colour_claim"] == audit["colour_claim"] == "red" or
            not proposal["direction"] == audit["direction"] == "negative_y" or
            track["points"] != audit["observed_track_points"]):
        raise ValueError("A008 audit does not match frozen right-area proposal")
    prior = next((row for row in output["ordered_candidates"] if row[
        "candidate_id"] == audit["prior_proposal"]["candidate_id"]), None)
    following = next((row for row in output["ordered_candidates"] if row[
        "candidate_id"] == audit["following_proposal"]["candidate_id"]), None)
    if (prior is None or following is None or
            prior["source_time_s"] != audit["prior_proposal"]["source_time_s"] or
            following["source_time_s"] != audit["following_proposal"]["source_time_s"] or
            prior["colour_claim"] != following["colour_claim"] != "yellow" or
            not prior["source_time_s"] < audit["source_time_s"] < following[
                "source_time_s"] or
            any(abs(row["source_time_s"] - audit["source_time_s"]) <= 15
                for row in output["ordered_candidates"] if row[
                    "observation_kind"] != "left_unconfirmed_raw_motion")):
        raise ValueError("A008 does not occupy the declared review gap")
    new = {
        "candidate_id": audit["candidate_id"],
        "source_time_s": audit["source_time_s"],
        "time_semantics": audit["time_semantics"],
        "colour_claim": audit["colour_claim"],
        "observation_kind": "right_area_reviewed_stone_pixels",
        "evidence_tier": "same_agent_short_stone_pixel_path_not_physical_throw",
        "left_screen_reason": None,
        "left_coverage_status": "sampled_left_activity_supported_but_no_left_stone_track",
        "observed_motion": {
            "status": "six_observed_right_area_colour_body_points",
            "source_interval_s": [track["points"][0]["time_s"],
                                  track["points"][-1]["time_s"]],
            "coordinate_frame": "right_camera_image_pixels",
            "points": deepcopy(track["points"]),
            "physical_stone_identity_verified": False,
        },
        "post_candidate_partial_board": None,
        "terminal_visibility": "unobserved_after_last_saved_point_not_physical_settle",
        "physical_throw_verified": False,
        "game_state_after": {
            "end_identity": None, "official_shot_identity": None,
            "release_time_s": None, "settle_time_s": None,
            "complete_board": None, "persistent_stone_ids": None,
            "metric_trajectory": None, "spin_revolution_count": None,
            "simulation_ready": False,
        },
        "source_pixel_review": {
            "source_pixel_class": audit["source_pixel_class"],
            "review_origin": audit["class_origin"],
            "image_path": "end1-omitted-right-area-source-audit/" + audit[
                "source_sheet"],
            "physical_throw_verified": False,
        },
        "source_area_scan_track_id": audit["raw_track_id"],
        "sequence_id": "P009a",
    }
    output["ordered_candidates"].append(new)
    output["ordered_candidates"].sort(key=lambda row: (
        row["source_time_s"], row["candidate_id"]))
    for index, row in enumerate(output["ordered_candidates"], 1):
        row["merged_order_index"] = index
    counts = Counter(row["observation_kind"] for row in output[
        "ordered_candidates"])
    if len(output["ordered_candidates"]) != 149 or counts[
            "right_area_reviewed_stone_pixels"] != 18:
        raise ValueError("Updated full-match candidate inventory differs")
    output["candidate_count"] = 149
    output["candidate_counts_by_kind"] = dict(counts)
    output["development_possible_event_review_count"] = 98
    output["end1_area_gap_candidate_count"] = 1
    output["status"] = "full_match_union_with_end1_end5_source_reviewed_area_gaps_not_throw_truth"
    output["limitations"].append(
        "An omitted end-one right-area red stone-pixel path adds one review proposal; 98 proposals are not a physical throw count or recall estimate."
    )
    if any(row["physical_throw_verified"] is not False or row[
            "game_state_after"]["simulation_ready"] is not False
           for row in output["ordered_candidates"]):
        raise ValueError("Physical event or simulation-ready state was promoted")
    return output
