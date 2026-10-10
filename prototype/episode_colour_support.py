"""Development-only colour refinement from motion within an event episode."""


def refine_episode_colours(candidates, decisions, *, max_delay_s=15,
                           support_ratio=1.5, min_local_ice=0.7):
    """Keep event timing, replacing colour only with stronger nearby support."""
    by_id = {item["id"]: item for item in candidates}
    decision_by_id = {row["id"]: row for row in decisions}
    if set(by_id) != set(decision_by_id):
        raise ValueError("Candidate and decision IDs differ")
    results = []
    for item in candidates:
        anchor = decision_by_id[item["id"]]
        if anchor["status"] != "corroborated_gap_candidate":
            continue
        start = item["crossing_time_s"]
        same_episode = [
            other for other in candidates
            if decision_by_id[other["id"]].get("episode_anchor_id") == item["id"]
            and start <= other["crossing_time_s"] <= start + max_delay_s
        ]
        own_support = max(
            decision_by_id[other["id"]]["moving_steps_gt4px"]
            for other in same_episode if other["colour"] == item["colour"]
        )
        opposite = [
            other for other in same_episode
            if other["colour"] != item["colour"]
            and decision_by_id[other["id"]]["median_local_ice_fraction"] >= min_local_ice
        ]
        challenger = max(
            opposite,
            key=lambda other: decision_by_id[other["id"]]["moving_steps_gt4px"],
            default=None,
        )
        challenger_support = (
            decision_by_id[challenger["id"]]["moving_steps_gt4px"]
            if challenger is not None else 0
        )
        changed = challenger is not None and challenger_support >= support_ratio * own_support
        results.append({
            "id": item["id"],
            "colour": challenger["colour"] if changed else item["colour"],
            "original_colour": item["colour"],
            "colour_support_id": challenger["id"] if changed else item["id"],
            "own_moving_steps": own_support,
            "challenger_moving_steps": challenger_support,
            "colour_changed": changed,
        })
    return results
