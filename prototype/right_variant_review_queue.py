"""Group same-source right-view proposals for review, without merging events."""


def build_review_queue(variants, *, window_s=8.0):
    """Return (proposals, groups); grouping is only a bounded review shortcut.

    Each variant maps a unique name to a sequence of proposals. A raw track can
    contribute multiple episodes, so its episode index is part of its identity.
    """
    if not variants or window_s < 0:
        raise ValueError("Need variants and a nonnegative window")
    proposals = []
    for variant, rows in sorted(variants.items()):
        if not variant or ":" in variant:
            raise ValueError("Variant names must be nonempty and contain no colon")
        for row in rows:
            episode = row.get("episode_index_within_raw_track", 1)
            if not isinstance(episode, int) or episode < 1:
                raise ValueError("Invalid episode index")
            proposal_id = f"{variant}:{row['raw_track_id']}:{episode}"
            proposals.append(
                {
                    "proposal_id": proposal_id,
                    "variant": variant,
                    "raw_track_id": row["raw_track_id"],
                    "episode_index_within_raw_track": episode,
                    "time_s": row["passage"]["time_s"],
                    "colour_claim": row["colour_claim"],
                    "direction": row["direction"],
                    "passage_pixel": row["passage"].get("pixel"),
                    "observed_prefix_interval_s": row["observed_prefix_interval_s"],
                    "physical_throw_identity_verified": False,
                    "simulation_ready": False,
                }
            )
    if len({p["proposal_id"] for p in proposals}) != len(proposals):
        raise ValueError("Duplicate proposal identity")
    proposals.sort(key=lambda p: (p["time_s"], p["proposal_id"]))

    groups = []
    for proposal in proposals:
        # Complete-linkage time bound avoids a 0, 7, 14 s transitive chain.
        eligible = [
            g
            for g in groups
            if g["colour_claim"] == proposal["colour_claim"]
            and g["direction"] == proposal["direction"]
            and proposal["time_s"] - g["first_time_s"] <= window_s
        ]
        if eligible:
            group = min(
                eligible, key=lambda g: (proposal["time_s"] - g["last_time_s"], g["group_id"])
            )
        else:
            group = {
                "group_id": f"R{len(groups) + 1:04d}",
                "colour_claim": proposal["colour_claim"],
                "direction": proposal["direction"],
                "first_time_s": proposal["time_s"],
                "last_time_s": proposal["time_s"],
                "proposal_ids": [],
                "review_group_not_physical_event": True,
            }
            groups.append(group)
        group["last_time_s"] = proposal["time_s"]
        group["proposal_ids"].append(proposal["proposal_id"])
        proposal["review_group_id"] = group["group_id"]
    assert sum(len(g["proposal_ids"]) for g in groups) == len(proposals)
    return proposals, groups
