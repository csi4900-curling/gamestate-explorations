"""Propose partial moving-stone evidence before ambiguous path splits."""

from math import dist


def propose_pre_split_motion(
    motion,
    patch,
    decision,
    *,
    min_samples=2,
    min_travel_m=1.0,
    min_scored_patches=2,
    min_positive_patches=2,
):
    """Return review evidence, never a verified physical throw or full track."""
    candidate_id = motion["candidate_id"]
    if candidate_id != patch["candidate_id"] or candidate_id != decision["candidate_id"]:
        raise ValueError("Candidate IDs differ")
    selection = motion["selection"]
    if (
        decision["accepted"]
        or decision["status"] == "duplicate_shared_timed_motion_path"
        or selection["status"] != "ambiguous_far_entry_motion_paths"
    ):
        return None
    prefix = selection.get("shared_prefix") or []
    if len(prefix) < min_samples:
        return None
    travel = dist(prefix[0]["ground_position_m"], prefix[-1]["ground_position_m"])
    if travel < min_travel_m:
        return None
    prefix_times = {node["source_time_s"] for node in prefix}
    scored = [
        sample
        for sample in patch["samples"]
        if sample["status"] == "scored" and sample["source_time_s"] in prefix_times
    ]
    positive = [sample for sample in scored if sample["patch_accepted"]]
    if len(scored) < min_scored_patches or len(positive) < min_positive_patches:
        return None
    return {
        "candidate_id": candidate_id,
        "status": "pre_split_stone_motion_review_proposal",
        "colour": motion["colour"],
        "receiving_view": motion["receiving_view"],
        "crossing_time_s": motion.get("crossing_time_s"),
        "prefix_samples": prefix,
        "prefix_sample_count": len(prefix),
        "first_ambiguity_time_s": selection.get("first_ambiguity_time_s"),
        "conditional_endpoint_displacement_m": round(travel, 4),
        "scored_patch_count": len(scored),
        "positive_patch_count": len(positive),
        "post_split_stone_identity_verified": False,
        "physical_throw_identity_verified": False,
        "simulation_ready": False,
    }


def deduplicate_identical_prefixes(proposals):
    """Collapse only exactly identical observed paths, with stable first IDs."""
    groups = {}
    for proposal in sorted(
        proposals,
        key=lambda row: (
            row["crossing_time_s"] is None,
            row["crossing_time_s"] if row["crossing_time_s"] is not None else 0,
            row["candidate_id"],
        ),
    ):
        key = (
            proposal["colour"],
            proposal["receiving_view"],
            tuple(
                (node["source_time_s"], tuple(node["pixel_center"]))
                for node in proposal["prefix_samples"]
            ),
        )
        if key not in groups:
            groups[key] = {**proposal, "duplicate_candidate_ids": []}
        else:
            groups[key]["duplicate_candidate_ids"].append(proposal["candidate_id"])
    return list(groups.values())
