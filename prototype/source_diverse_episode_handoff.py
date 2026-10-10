"""Attach source-diverse right-path evidence to lossless cross-view episodes."""

from collections import Counter


def build_episode_handoff(episodes, partial_states, patch_scores, audits, overlap_rows=None):
    """Join evidence by exact IDs without accepting or removing physical events."""
    episode_rows = episodes["episodes"]
    state_by_id = {row["episode_id"]: row for row in partial_states["episodes"]}
    score_by_id = {row["right_proposal_id"]: row for row in patch_scores["rows"]}
    if len(state_by_id) != len(partial_states["episodes"]) or len(score_by_id) != len(
        patch_scores["rows"]
    ):
        raise ValueError("Duplicate state episode or right-path score")
    reviewed_by_id = {}
    for audit_name, audit in audits.items():
        for row in audit["rows"]:
            pid = row["right_proposal_id"]
            if pid in reviewed_by_id:
                raise ValueError(f"Duplicate source review: {pid}")
            reviewed_by_id[pid] = {
                "sampled_source_pixel_class": row["sampled_source_pixel_class"],
                "source_pixel_audit": audit_name,
                "source_pixel_page": row["page"],
                "source_sample_times_s": row["source_sample_times_s"],
            }
    if set(state_by_id) != {row["episode_id"] for row in episode_rows}:
        raise ValueError("Episode/state IDs differ")
    overlap_by_pair = {
        (row["left_candidate_id"], row["right_proposal_id"]): row for row in (overlap_rows or [])
    }
    if overlap_rows is not None and len(overlap_by_pair) != len(overlap_rows):
        raise ValueError("Duplicate cross-resolution candidate pair")
    rows = []
    seen_right = []
    seen_left = []
    seen_overlap = []
    for episode in episode_rows:
        eid = episode["episode_id"]
        state = state_by_id[eid]
        if (
            state["right_proposal_ids"] != episode["right_proposal_ids"]
            or state["episode_kind"] != episode["episode_kind"]
            or [r["interval_candidate_id"] for r in state["left_members"]]
            != episode["member_left_candidate_ids"]
        ):
            raise ValueError(f"Episode/state membership differs: {eid}")
        right_evidence = []
        for pid in episode["right_proposal_ids"]:
            score = score_by_id[pid]
            review = reviewed_by_id.get(pid)
            if review and (
                review["source_sample_times_s"] != [sample["time_s"] for sample in score["samples"]]
                or (
                    review["sampled_source_pixel_class"] == "moving_stone_pixels"
                    and not score["any_positive_patch"]
                )
            ):
                raise ValueError(f"Source review/score mismatch: {pid}")
            right_evidence.append(
                {
                    "right_proposal_id": pid,
                    "passage_time_s": score["passage_time_s"],
                    "positive_patch_count": score["positive_patch_count"],
                    "sampled_patch_count": len(score["samples"]),
                    "any_positive_patch": score["any_positive_patch"],
                    "sampled_source_pixel_class": (
                        review["sampled_source_pixel_class"] if review else None
                    ),
                    "source_pixel_audit": review["source_pixel_audit"] if review else None,
                    "source_pixel_page": review["source_pixel_page"] if review else None,
                    "physical_stone_identity_verified": False,
                }
            )
            seen_right.append(pid)
        seen_left.extend(episode["member_left_candidate_ids"])
        cross_resolution_pairs = []
        for lid in episode["member_left_candidate_ids"]:
            for pid in episode["right_proposal_ids"]:
                pair = overlap_by_pair.get((lid, pid))
                if pair is None:
                    continue
                cross_resolution_pairs.append(
                    {
                        "left_candidate_id": lid,
                        "right_proposal_id": pid,
                        "sampled_time_overlap_count": pair["sampled_time_overlap_count"],
                        "median_center_distance_px_360": pair["median_center_distance_px_360"],
                        "physical_stone_identity_verified": False,
                    }
                )
                seen_overlap.append((lid, pid))
        stone_prefix_ids = [
            row["right_proposal_id"]
            for row in right_evidence
            if row["sampled_source_pixel_class"] == "moving_stone_pixels"
        ]
        unreviewed_positive_ids = [
            row["right_proposal_id"]
            for row in right_evidence
            if row["any_positive_patch"] and row["sampled_source_pixel_class"] is None
        ]
        if stone_prefix_ids:
            priority = "review_stone_prefix_cross_view_identity_and_board"
        elif unreviewed_positive_ids:
            priority = "review_unreviewed_stone_like_right_prefix"
        elif right_evidence and not episode["member_left_candidate_ids"]:
            priority = "review_right_only_person_prefix_and_left_coverage"
        elif right_evidence:
            priority = "review_left_candidate_or_missing_right_stone"
        else:
            priority = "review_left_without_right_candidate"
        rows.append(
            {
                **state,
                "right_proposal_evidence": right_evidence,
                "cross_resolution_candidate_pair_evidence": cross_resolution_pairs,
                "source_reviewed_stone_prefix_right_ids": stone_prefix_ids,
                "unreviewed_positive_right_ids": unreviewed_positive_ids,
                "evidence_review_priority": priority,
                "physical_throw_count_verified": False,
                "cross_view_identity_verified": False,
                "complete_game_state": False,
                "simulation_ready": False,
            }
        )
    expected_left = episodes["original_left_candidate_count"]
    expected_right = episodes["right_proposal_count"]
    if (
        len(rows) != episodes["episode_count"]
        or len(seen_left) != expected_left
        or len(set(seen_left)) != expected_left
        or len(seen_right) != expected_right
        or len(set(seen_right)) != expected_right
        or set(seen_right) != set(score_by_id)
        or set(seen_overlap) != set(overlap_by_pair)
        or len(seen_overlap) != len(overlap_by_pair)
        or not set(reviewed_by_id).issubset(seen_right)
    ):
        raise ValueError("Episode candidate conservation failed")
    if any(
        row["simulation_ready"]
        or row["complete_game_state"]
        or row["physical_throw_count_verified"]
        or row["cross_view_identity_verified"]
        for row in rows
    ):
        raise ValueError("Provisional handoff promoted unsupported state")
    return rows, dict(Counter(row["evidence_review_priority"] for row in rows))
