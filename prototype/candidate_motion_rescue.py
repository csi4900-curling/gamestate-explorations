"""Provisional dropout rescue for a candidate lacking a unique receiving path.

This stage reads camera observations only. It does not score events or use labels.
"""

from copy import deepcopy
from math import dist

from stone_proposal_path import select_far_entry_motion_path

BRIDGE_ELIGIBLE = "bridge_eligible_missing_far_cap_or_registration"
SUPPORTED_STATUS = {
    "provisional_unique_far_entry_motion_path",
    "provisional_unique_dropout_rescue_motion_path",
    "provisional_shared_prefix_motion_evidence",
}


def mark_bridge_eligible(samples, colour, view, far_band_y_m=2.0):
    """Allow a gap where no distant same-colour proposal was detected."""
    if view not in ("left", "right") or far_band_y_m <= 0:
        raise ValueError("Invalid receiving view or far-band boundary")
    marked = deepcopy(samples)
    for sample in marked:
        if sample.get("status") == "abstained_no_stable_anchor" or (
                sample.get("registration_status") not in (None, "registered")):
            sample["status"] = BRIDGE_ELIGIBLE
            continue
        distant = any(
            proposal["colour"] == colour and
            proposal["ground_position_m"] is not None and
            (proposal["ground_position_m"][1] <= -far_band_y_m if view == "left"
             else proposal["ground_position_m"][1] >= far_band_y_m)
            for proposal in sample["views"][view]["proposals"])
        if not distant:
            sample["status"] = BRIDGE_ELIGIBLE
    return marked


def rescue_candidate_path(base_selection, samples, colour, view, *,
                          far_band_y_m=2.0, right_entry_y_m=11.5,
                          left_entry_y_m=-4.5, max_gap_s=4.1,
                          min_prefix_samples=5, min_prefix_fraction=0.7,
                          min_prefix_travel_m=2.0):
    """Keep an existing unique path; otherwise attempt one bounded rescue."""
    if base_selection["status"] == "provisional_unique_far_entry_motion_path":
        return {"selection": deepcopy(base_selection),
                "rescue_status": "baseline_path_preserved"}
    marked = mark_bridge_eligible(samples, colour, view, far_band_y_m)
    kwargs = ({"view": "left", "entry_y_threshold_m": left_entry_y_m,
               "forward_direction": 1, "min_samples": 4,
               "max_forward_speed_change_m_s": 2.0}
              if view == "left" else
              {"view": "right", "entry_y_threshold_m": right_entry_y_m})
    trial = select_far_entry_motion_path(
        marked, colour, max_gap_s=max_gap_s,
        allow_missing_samples=True,
        skip_status_required=BRIDGE_ELIGIBLE, **kwargs)
    if trial["status"] == "provisional_unique_far_entry_motion_path":
        trial["status"] = "provisional_unique_dropout_rescue_motion_path"
        trial["physical_identity_verified"] = False
        trial["metric_accuracy_verified"] = False
        trial["simulation_ready"] = False
        return {"selection": trial,
                "rescue_status": "unique_dropout_rescue"}
    prefix = trial.get("shared_prefix", [])
    best_length = trial.get("best_path_sample_count", 0)
    if (trial["status"] == "ambiguous_far_entry_motion_paths" and
            best_length and len(prefix) >= min_prefix_samples and
            len(prefix) / best_length >= min_prefix_fraction and
            dist(prefix[0]["ground_position_m"],
                 prefix[-1]["ground_position_m"]) >= min_prefix_travel_m):
        return {"selection": {
                    "status": "provisional_shared_prefix_motion_evidence",
                    "path": prefix,
                    "sample_count": len(prefix),
                    "best_path_sample_count": best_length,
                    "shared_prefix_fraction": len(prefix) / best_length,
                    "endpoint_displacement_m": dist(
                        prefix[0]["ground_position_m"],
                        prefix[-1]["ground_position_m"]),
                    "first_ambiguity_time_s": trial.get("first_ambiguity_time_s"),
                    "observation_after_prefix_verified": False,
                    "release_time_observed": False,
                    "physical_identity_verified": False,
                    "metric_accuracy_verified": False,
                    "simulation_ready": False,
                },
                "rescue_status": "shared_prefix_only_after_ambiguity"}
    return {"selection": trial, "rescue_status": "rescue_abstained"}
