"""Conditional receiving-view routing for two-panel throw candidates."""

from collections import Counter


def route_split_post_board_views(sequence):
    """Route by right-path direction and cross-panel chronology, never by score.

    The result is a camera hypothesis for where post-event board pixels should
    be sampled. It does not verify that the candidate is a physical throw.
    """
    right_rows = sequence["right_proposals"]
    by_right = {row["proposal_id"]: row for row in right_rows}
    if len(by_right) != len(right_rows):
        raise ValueError("Duplicate right proposal ID")
    left_rows = [
        row for row in sequence["rows"] if row["observation_kind"] == "left_tracked_passage"
    ]
    if len(left_rows) != sequence["left_candidate_count"]:
        raise ValueError("Left candidate count differs from sequence")
    if len({row["candidate_id"] for row in left_rows}) != len(left_rows):
        raise ValueError("Duplicate left candidate ID")

    routed = []
    for row in left_rows:
        ids = row["right_temporal_candidate_ids"]
        if len(ids) == 0:
            status, view, proposal, lag = "abstain_no_unique_right_link", None, None, None
        elif len(ids) != 1:
            status, view, proposal, lag = "abstain_competing_right_links", None, None, None
        else:
            proposal = ids[0]
            if proposal not in by_right:
                raise ValueError(f"Unknown right proposal {proposal}")
            right = by_right[proposal]
            if row["colour_claim"] != right["colour_claim"]:
                raise ValueError("Left/right candidate colours differ")
            lag = round(right["passage_time_s"] - row["observation_time_s"], 3)
            if right["direction"] == "positive_y" and lag < 0:
                status, view = "conditional_receiving_view_from_direction_and_order", "left"
            elif right["direction"] == "negative_y" and lag > 0:
                status, view = "conditional_receiving_view_from_direction_and_order", "right"
            else:
                status, view = "abstain_direction_order_conflict", None
        observed_board = row.get("post_candidate_partial_cap_observation")
        routed.append(
            {
                "candidate_id": row["candidate_id"],
                "observation_time_s": row["observation_time_s"],
                "colour_claim": row["colour_claim"],
                "right_proposal_id": proposal,
                "right_minus_left_passage_lag_s": lag,
                "routing_status": status,
                "conditional_receiving_view": view,
                "existing_post_candidate_scan_view": "right"
                if observed_board is not None
                else None,
                "existing_post_candidate_scan_status": observed_board["status"]
                if observed_board
                else None,
                "existing_scan_samples_conditional_receiving_view": (view == "right")
                if observed_board is not None and view
                else None,
                "physical_throw_verified": False,
                "complete_board_verified": False,
                "simulation_ready": False,
            }
        )
    counts = Counter(row["routing_status"] for row in routed)
    views = Counter(
        row["conditional_receiving_view"] for row in routed if row["conditional_receiving_view"]
    )
    return {
        "source_sha256": sequence["source_sha256"],
        "left_candidate_count": len(left_rows),
        "routing_status_counts": dict(counts),
        "conditional_receiving_view_counts": dict(views),
        "existing_right_scan_wrong_view_count_conditional": sum(
            row["existing_post_candidate_scan_view"] == "right"
            and row["conditional_receiving_view"] == "left"
            for row in routed
        ),
        "rows": routed,
        "limitations": [
            "View is conditional on a provisional right/left event link, not physical stone identity.",
            "Direction and chronology are interpreted for the 2024 two-panel layout only.",
            "No new board pixels are scanned and no physical game state is promoted.",
        ],
    }
