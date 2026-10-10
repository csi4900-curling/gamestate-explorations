"""Account for every frozen full-right right-only proposal in the match ledger."""

from collections import Counter
from copy import deepcopy


def reconcile_full_right_only(ledger, episodes, scan, nonstone_audit):
    output = deepcopy(ledger)
    if (not ledger["source_sha256"] == episodes["source_sha256"] == scan[
            "source_sha256"] == nonstone_audit["source_video_sha256"] or
            ledger["candidate_count"] != 149 or
            ledger["development_possible_event_review_count"] != 98 or
            len(nonstone_audit["rows"]) != 3):
        raise ValueError("Right-only reconciliation inputs differ")
    by_id = {row["candidate_id"]: row for row in output["ordered_candidates"]}
    if len(by_id) != 149:
        raise ValueError("Existing candidate IDs are not unique")
    proposals = {"R01:" + row["raw_track_id"]: row for row in scan[
        "directional_review_proposals"]}
    tracks = {"R01:" + row["track_id"]: row for row in scan["raw_tracks"]}
    if (len(proposals) != scan["directional_proposal_count"] or
            len(tracks) != scan["raw_track_count"]):
        raise ValueError("Frozen right track or proposal IDs are not unique")
    right_only = [row for row in episodes["episodes"] if row[
        "episode_kind"] == "right_only_candidate"]
    if (len(right_only) != 32 or
            len({row["right_proposal_ids"][0] for row in right_only
                 if len(row["right_proposal_ids"]) == 1}) != 32 or
            any(len(row["right_proposal_ids"]) != 1 for row in right_only)):
        raise ValueError("Frozen right-only episode inventory differs")
    audits = {row["candidate_id"]: row for row in nonstone_audit["rows"]}
    if len(audits) != 3:
        raise ValueError("Duplicate nonstone audit IDs")
    old_right = [row for row in output["ordered_candidates"] if row[
        "observation_kind"] == "right_only_review_entry"]
    if len(old_right) != 8:
        raise ValueError("Older right-only inventory differs")
    used_legacy = set()
    used_audits = set()
    accounting = []
    additions = []
    for episode in right_only:
        rid = episode["right_proposal_ids"][0]
        candidate_id = "right_area:" + rid
        proposal = proposals.get(rid)
        track = tracks.get(rid)
        if (proposal is None or track is None or
                episode["observation_time_s"] != proposal["passage"]["time_s"] or
                episode["colour_claim"] != proposal["colour_claim"] or
                episode["direction"] != proposal["direction"]):
            raise ValueError(f"Right-only episode cannot join frozen scan: {rid}")
        if candidate_id in by_id:
            candidate = by_id[candidate_id]
            if (candidate["observation_kind"] not in (
                    "right_area_reviewed_stone_pixels",
                    "right_area_reviewed_person_pixels") or
                    candidate["source_time_s"] != episode[
                        "observation_time_s"] or
                    candidate["colour_claim"] != episode["colour_claim"]):
                raise ValueError(f"Existing area candidate differs: {rid}")
            accounting.append({"right_proposal_id": rid,
                               "episode_id": episode["episode_id"],
                               "accounting": "existing_area_candidate",
                               "candidate_id": candidate_id})
            continue
        matches = [row for row in old_right if row["colour_claim"] == episode[
            "colour_claim"] and abs(row["source_time_s"] - episode[
                "observation_time_s"]) <= 5]
        if matches:
            if len(matches) != 1 or matches[0]["candidate_id"] in used_legacy:
                raise ValueError(f"Legacy right-only mapping ambiguous: {rid}")
            matched = matches[0]
            used_legacy.add(matched["candidate_id"])
            accounting.append({"right_proposal_id": rid,
                               "episode_id": episode["episode_id"],
                               "accounting": "paired_older_right_entry_not_identity_proof",
                               "candidate_id": matched["candidate_id"],
                               "source_pixel_class": None})
            continue
        audit = audits.get(candidate_id)
        if (audit is None or candidate_id in used_audits or
                audit["raw_track_id"] != rid.removeprefix("R01:") or
                audit["episode_id"] != episode["episode_id"] or
                audit["source_time_s"] != episode["observation_time_s"] or
                audit["colour_claim"] != episode["colour_claim"] or
                audit["direction"] != episode["direction"] or
                audit["observed_track_points"] != track["points"] or
                audit["physical_throw_verified"] is not False or
                audit["source_pixel_class"] not in (
                    "broom_or_player_equipment_pixels",
                    "person_jacket_logo_pixels",
                    "person_clothing_or_wheelchair_pixels")):
            raise ValueError(f"Unrepresented right-only proposal lacks review: {rid}")
        used_audits.add(candidate_id)
        additions.append({
            "candidate_id": candidate_id,
            "source_time_s": audit["source_time_s"],
            "time_semantics": audit["time_semantics"],
            "colour_claim": audit["colour_claim"],
            "observation_kind": "right_area_reviewed_nonstone_pixels",
            "evidence_tier": "same_agent_nonstone_pixel_path_not_throw",
            "left_screen_reason": None,
            "left_coverage_status": "right_area_source_review_no_left_stone_link",
            "observed_motion": {
                "coordinate_frame": "right_camera_image_pixels",
                "points": deepcopy(track["points"]),
                "physical_stone_identity_verified": False,
            },
            "post_candidate_partial_board": None,
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
                "image_path": "remaining-right-only-source-audit/" + audit[
                    "source_sheet"],
                "physical_throw_verified": False,
            },
            "source_area_scan_track_id": audit["raw_track_id"],
            "sequence_id": "RIGHT_ONLY_" + episode["episode_id"],
        })
        accounting.append({"right_proposal_id": rid,
                           "episode_id": episode["episode_id"],
                           "accounting": "source_reviewed_nonstone_abstention_added",
                           "candidate_id": candidate_id,
                           "source_pixel_class": audit["source_pixel_class"]})
    kinds = Counter(row["accounting"] for row in accounting)
    if (kinds != {"existing_area_candidate": 22,
                  "paired_older_right_entry_not_identity_proof": 7,
                  "source_reviewed_nonstone_abstention_added": 3} or
            used_audits != set(audits) or len(used_legacy) != 7):
        raise ValueError("Right-only accounting incomplete")
    unmatched_legacy = [row["candidate_id"] for row in old_right if row[
        "candidate_id"] not in used_legacy]
    if unmatched_legacy != ["right:R008"]:
        raise ValueError("Unexpected old right-only area nonmatch")
    output["ordered_candidates"].extend(additions)
    output["ordered_candidates"].sort(key=lambda row: (
        row["source_time_s"], row["candidate_id"]))
    for index, row in enumerate(output["ordered_candidates"], 1):
        row["merged_order_index"] = index
    counts = Counter(row["observation_kind"] for row in output[
        "ordered_candidates"])
    if len(output["ordered_candidates"]) != 152 or counts[
            "right_area_reviewed_nonstone_pixels"] != 3:
        raise ValueError("Final candidate inventory differs")
    output["candidate_count"] = 152
    output["candidate_counts_by_kind"] = dict(counts)
    output["right_area_right_only_accounted_count"] = 32
    output["right_area_right_only_accounting_counts"] = dict(kinds)
    output["right_area_right_only_accounting"] = accounting
    output["older_right_only_without_full_area_match"] = unmatched_legacy
    output["status"] = "full_match_union_all_frozen_area_right_only_accounted_not_throw_truth"
    output["limitations"].append(
        "All 32 frozen full-right right-only proposals are inventoried, but seven old-entry matches are time/colour joins rather than proven stone identities and one old right entry lacks an area match."
    )
    if (output["development_possible_event_review_count"] != 98 or
            output["physical_throw_count_verified"] is not None or
            any(row["physical_throw_verified"] is not False or row[
                "game_state_after"]["simulation_ready"] is not False
                for row in output["ordered_candidates"])):
        raise ValueError("Nonstone accounting promoted events or states")
    return output
