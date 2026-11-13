"""Direction-aware two-view proposal corroboration without physical identity."""


def corroborate_left_proposals(left_events, right_proposals, *, max_lag_s=20):
    if max_lag_s <= 0:
        raise ValueError("Invalid maximum lag")
    if len({row["id"] for row in left_events}) != len(left_events):
        raise ValueError("Duplicate left candidate ID")
    if len({row["proposal_id"] for row in right_proposals}) != len(right_proposals):
        raise ValueError("Duplicate right proposal ID")
    rows = []
    for left in left_events:
        direction = left["view_motion"]
        t = left["crossing_time_s"]
        matches = []
        for right in right_proposals:
            if right["colour_claim"] != left["colour"] or right["direction"] != direction:
                continue
            lag = (
                t - right["passage_time_s"]
                if direction == "positive_y"
                else right["passage_time_s"] - t
                if direction == "negative_y"
                else None
            )
            if lag is not None and 0 <= lag <= max_lag_s:
                matches.append(
                    {
                        "right_proposal_id": right["proposal_id"],
                        "view_order_lag_s": round(lag, 3),
                        "right_context_tier": right.get("context_tier"),
                    }
                )
        matches.sort(key=lambda row: (row["view_order_lag_s"], row["right_proposal_id"]))
        rows.append(
            {
                "left_candidate_id": left["id"],
                "left_passage_time_s": t,
                "colour_claim": left["colour"],
                "direction": direction,
                "matching_right_proposals": matches,
                "match_count": len(matches),
                "physical_stone_identity_verified": False,
            }
        )
    competing = {}
    for row in rows:
        for match in row["matching_right_proposals"]:
            rid = match["right_proposal_id"]
            competing.setdefault(rid, []).append(row["left_candidate_id"])
    for row in rows:
        row["unique_right_candidate_ids"] = [
            match["right_proposal_id"]
            for match in row["matching_right_proposals"]
            if len(competing[match["right_proposal_id"]]) == 1
        ]
        row["shared_right_candidate_ids"] = [
            match["right_proposal_id"]
            for match in row["matching_right_proposals"]
            if len(competing[match["right_proposal_id"]]) > 1
        ]
        row["corroboration_tier"] = (
            "unique_right_time_colour_direction_candidate"
            if len(row["unique_right_candidate_ids"]) == 1
            and not row["shared_right_candidate_ids"]
            and row["match_count"] == 1
            else "ambiguous_right_candidates"
            if row["match_count"]
            else "no_right_time_colour_direction_candidate"
        )
    return rows
