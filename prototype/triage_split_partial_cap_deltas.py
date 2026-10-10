"""Review tiers for image cap visibility changes, not physical transitions."""

from collections import Counter


def triage_deltas(delta, context):
    if delta["source_sha256"] != context["source_sha256"]:
        raise ValueError("Source fingerprints differ")
    context_by_key = {(row["candidate_id"], row["phase"],
                       row["local_observation_id"]): row
                      for row in context["rows"]}
    if len(context_by_key) != len(context["rows"]):
        raise ValueError("Duplicate cap context key")
    rows = []
    for item in delta["rows"]:
        change = item["image_cap_delta"]
        changed = []
        if change is None:
            tier = "window_or_scene_abstention"
        elif change["unresolved_before"] or change["unresolved_after"]:
            tier = "ambiguous_local_match_review"
        else:
            for phase, key in (("pre", "no_longer_observed"),
                               ("post", "newly_observed")):
                for local_id in change[key]:
                    lookup = (item["candidate_id"], phase, local_id)
                    cap = context_by_key.get(lookup)
                    if cap is None:
                        raise ValueError(f"Missing context for changed cap: {lookup}")
                    changed.append({
                        "phase": phase,
                        "local_observation_id": local_id,
                        "colour": cap["colour"],
                        "pixel_center": cap["pixel_center"],
                        "context_tier": cap["context_tier"],
                    })
            if not changed:
                tier = "no_visible_cap_change"
            elif any(cap["context_tier"] == "context_cluttered_review"
                     for cap in changed):
                tier = "cluttered_change_review"
            elif any(cap["context_tier"] == "context_unavailable_review"
                     for cap in changed):
                tier = "context_unavailable_change_review"
            else:
                tier = "clear_context_change_review"
        rows.append({
            "candidate_id": item["candidate_id"],
            "comparison_status": item["comparison_status"],
            "review_tier": tier,
            "changed_cap_context": changed,
            "physical_transition_verified": False,
            "complete_board_verified": False,
            "simulation_ready": False,
        })
    return {"candidate_count": len(rows),
            "review_tier_counts": dict(Counter(row["review_tier"] for row in rows)),
            "rows": rows}
