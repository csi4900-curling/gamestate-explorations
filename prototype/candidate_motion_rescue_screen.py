"""Stone-appearance screen for unique paths and bounded shared prefixes."""

from candidate_motion_rescue import SUPPORTED_STATUS


def screen_rescue_candidate(motion_row, patch_row):
    if motion_row["candidate_id"] != patch_row["candidate_id"]:
        raise ValueError("Candidate IDs differ")
    selection = motion_row["selection"]
    status = selection["status"]
    if status not in SUPPORTED_STATUS or not selection.get("path"):
        return {
            "candidate_id": motion_row["candidate_id"],
            "status": "abstain_no_supported_motion_path",
            "accepted": False,
            "physical_identity_verified": False,
        }
    samples = patch_row["samples"]
    scored = [sample for sample in samples if sample["status"] == "scored"]
    accepted = any(sample["patch_accepted"] for sample in scored)
    if accepted:
        decision_status = (
            "provisional_shared_prefix_and_patch_support"
            if status == "provisional_shared_prefix_motion_evidence"
            else "provisional_motion_and_patch_support"
        )
    elif samples and len(scored) == len(samples):
        decision_status = "motion_without_stone_like_patch_support"
    else:
        decision_status = "abstain_incomplete_patch_check"
    return {
        "candidate_id": motion_row["candidate_id"],
        "status": decision_status,
        "accepted": accepted,
        "motion_status": status,
        "scored_patch_count": len(scored),
        "accepted_patch_count": sum(sample["patch_accepted"] for sample in scored),
        "motion_sample_count": selection["sample_count"],
        "physical_identity_verified": False,
    }
