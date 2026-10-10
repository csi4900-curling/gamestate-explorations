"""Combine candidate-centric motion and frozen patch appearance conservatively."""


def screen_candidate(motion_row, patch_row):
    if motion_row["candidate_id"] != patch_row["candidate_id"]:
        raise ValueError("Candidate IDs differ")
    selection = motion_row["selection"]
    if selection["status"] != "provisional_unique_far_entry_motion_path":
        return {"candidate_id": motion_row["candidate_id"],
                "status": "abstain_no_unique_motion_path",
                "accepted": False,
                "physical_identity_verified": False}
    samples = patch_row["samples"]
    scored = [sample for sample in samples if sample["status"] == "scored"]
    if any(sample["patch_accepted"] for sample in scored):
        status = "provisional_motion_and_patch_support"
        accepted = True
    elif len(scored) == len(samples) and samples:
        status = "motion_without_stone_like_patch_support"
        accepted = False
    else:
        status = "abstain_incomplete_patch_check"
        accepted = False
    return {"candidate_id": motion_row["candidate_id"],
            "status": status, "accepted": accepted,
            "scored_patch_count": len(scored),
            "accepted_patch_count": sum(s["patch_accepted"] for s in scored),
            "motion_sample_count": selection["sample_count"],
            "physical_identity_verified": False}
