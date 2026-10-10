"""Retain a strong original path prefix when a broad retry becomes ambiguous."""

from math import dist


def propose_original_prefix(base, retry, patch, *, min_samples=5,
                            min_fraction=0.7, min_travel_m=2.0,
                            min_scored_patches=3, min_positive_patches=2):
    """Return a partial motion proposal, never a confirmed physical throw."""
    if not (base["candidate_id"] == retry["candidate_id"] ==
            patch["candidate_id"]):
        raise ValueError("Candidate IDs differ")
    selection = base["selection"]
    if (selection["status"] != "ambiguous_far_entry_motion_paths" or
            retry["rescue_status"] != "rescue_abstained"):
        return None
    prefix = selection.get("shared_prefix", [])
    best_length = selection.get("best_path_sample_count", 0)
    if (not best_length or len(prefix) < min_samples or
            len(prefix) / best_length < min_fraction):
        return None
    travel = dist(prefix[0]["ground_position_m"],
                  prefix[-1]["ground_position_m"])
    if travel < min_travel_m:
        return None
    prefix_times = {point["source_time_s"] for point in prefix}
    scored = [sample for sample in patch["samples"]
              if sample["status"] == "scored" and
              sample["source_time_s"] in prefix_times]
    positives = [sample for sample in scored if sample["patch_accepted"]]
    if len(scored) < min_scored_patches or len(positives) < min_positive_patches:
        return None
    return {
        "candidate_id": base["candidate_id"],
        "status": "development_original_prefix_only_motion_proposal",
        "receiving_view": base["receiving_view"],
        "colour": base["colour"],
        "original_prefix": prefix,
        "prefix_sample_count": len(prefix),
        "best_original_path_sample_count": best_length,
        "prefix_fraction": round(len(prefix) / best_length, 4),
        "prefix_endpoint_displacement_m_conditional": round(travel, 4),
        "scored_patch_count": len(scored),
        "positive_patch_count": len(positives),
        "first_ambiguity_time_s": selection.get("first_ambiguity_time_s"),
        "motion_after_ambiguity_verified": False,
        "physical_throw_identity_verified": False,
        "simulation_ready": False,
    }
