"""Retain observed travel before a motion path splits into alternatives."""

from math import dist


def propose_shared_prefix(
    motion,
    patch,
    *,
    min_samples=5,
    min_fraction=0.7,
    min_travel_m=2.0,
    min_scored_patches=3,
    min_positive_patches=2,
):
    """Return a partial review proposal; never a confirmed physical throw."""
    if motion["candidate_id"] != patch["candidate_id"]:
        raise ValueError("Candidate IDs differ")
    selection = motion["selection"]
    if selection["status"] != "ambiguous_far_entry_motion_paths":
        return None
    prefix = selection.get("shared_prefix") or []
    best_length = selection.get("best_path_sample_count", 0)
    if best_length <= 0 or len(prefix) < min_samples or len(prefix) / best_length < min_fraction:
        return None
    travel = dist(prefix[0]["ground_position_m"], prefix[-1]["ground_position_m"])
    if travel < min_travel_m:
        return None
    prefix_times = {point["source_time_s"] for point in prefix}
    scored = [
        sample
        for sample in patch["samples"]
        if sample["status"] == "scored" and sample["source_time_s"] in prefix_times
    ]
    positives = [sample for sample in scored if sample["patch_accepted"]]
    if len(scored) < min_scored_patches or len(positives) < min_positive_patches:
        return None
    return {
        "candidate_id": motion["candidate_id"],
        "status": "partial_shared_prefix_motion_review_proposal",
        "colour": motion["colour"],
        "receiving_view": motion["receiving_view"],
        "prefix_samples": prefix,
        "prefix_sample_count": len(prefix),
        "best_path_sample_count": best_length,
        "prefix_fraction": round(len(prefix) / best_length, 4),
        "conditional_endpoint_displacement_m": round(travel, 4),
        "scored_patch_count": len(scored),
        "positive_patch_count": len(positives),
        "first_ambiguity_time_s": selection.get("first_ambiguity_time_s"),
        "motion_after_ambiguity_verified": False,
        "physical_throw_identity_verified": False,
        "simulation_ready": False,
    }
