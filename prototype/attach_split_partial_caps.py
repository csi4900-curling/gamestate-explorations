"""Attach visible cap observations to candidate rows without asserting game state."""

from collections import Counter
from copy import deepcopy


def attach_partial_caps(sequence, scan):
    if sequence["source_sha256"] != scan["source_sha256"]:
        raise ValueError("Source fingerprints differ")
    left_ids = {row["candidate_id"] for row in sequence["rows"]
                if row["observation_kind"] == "left_tracked_passage"}
    scan_by_id = {row["candidate_id"]: row for row in scan["rows"]}
    if (len(scan_by_id) != len(scan["rows"]) or set(scan_by_id) != left_ids
            or len(left_ids) != sequence["left_candidate_count"]):
        raise ValueError("Partial-cap scan must cover every left candidate exactly once")
    result = deepcopy(sequence)
    for row in result["rows"]:
        evidence = scan_by_id.get(row["candidate_id"])
        if evidence is None:
            row["post_candidate_partial_cap_observation"] = None
            continue
        if (evidence["left_event_id"] != row["left_event_id"]
                or evidence["observed_left_passage_time_s"] != row["observation_time_s"]
                or evidence["complete_board_verified"]
                or evidence["physical_settle_verified"]
                or evidence["simulation_ready"]):
            raise ValueError("Partial-cap row disagrees with candidate or promotes physical state")
        row["post_candidate_partial_cap_observation"] = {
            "status": evidence["observation_status"],
            "sample_times_s": evidence["sample_times_s"],
            "scene_mae_between_samples": evidence["scene_mae_between_samples"],
            "coordinate_frame": evidence["coordinate_frame"],
            "stable_cap_proposals": evidence["stable_cap_proposals"],
            "complete_board_verified": False,
            "physical_settle_verified": False,
            "persistent_stone_identity_verified": False,
            "simulation_ready": False,
        }
        if row["game_state_after"]["complete_board"] is not None:
            raise ValueError("Partial caps cannot be joined to an asserted complete board")
    result["partial_cap_observation_status_counts"] = dict(Counter(
        item["observation_status"] for item in scan["rows"]))
    result["stable_cap_proposal_count"] = sum(
        len(item["stable_cap_proposals"]) for item in scan["rows"])
    result["status"] = "candidate_sequence_with_partial_post_candidate_cap_observations"
    return result
