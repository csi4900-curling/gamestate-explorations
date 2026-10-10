"""Group passage candidates around an observed, stone-like shared path prefix.

The result is a review-level episode proposal, not a verified physical throw.
"""


def build_partial_episode_union(handoff, prefix_audit, motion):
    timeline = handoff["timeline"]
    by_id = {row["candidate_id"]: row for row in timeline}
    motion_rows = {row["candidate_id"]: row for row in motion["rows"]}
    if len(by_id) != len(timeline) or len(motion_rows) != len(motion["rows"]):
        raise ValueError("Duplicate candidate ID")
    if not set(motion_rows) <= set(by_id):
        raise ValueError("Motion candidate missing from timeline")
    proposals = prefix_audit["proposals"]
    roots = [row["candidate_id"] for row in proposals]
    if len(set(roots)) != len(roots):
        raise ValueError("Duplicate partial-prefix root")
    episodes = []
    claimed = set()
    for index, proposal in enumerate(proposals, 1):
        root = proposal["candidate_id"]
        if root not in motion_rows or by_id[root]["event_status"] != "screen_abstention":
            raise ValueError(f"Partial-prefix root is not a screened abstention: {root}")
        if proposal["colour"] != by_id[root]["candidate_colour"] or \
                proposal["receiving_view"] != motion_rows[root]["receiving_view"]:
            raise ValueError(f"Partial-prefix colour/view mismatch: {root}")
        samples = proposal["prefix_samples"]
        times = [sample["source_time_s"] for sample in samples]
        if not times or times != sorted(set(times)):
            raise ValueError(f"Invalid observed prefix timestamps: {root}")
        start, end = times[0], times[-1]
        if proposal["first_ambiguity_time_s"] is not None and \
                proposal["first_ambiguity_time_s"] <= end:
            raise ValueError(f"Prefix extends past first ambiguity: {root}")
        if any(row["event_status"] == "provisional_event" and
               row["candidate_colour"] == proposal["colour"] and
               start <= row["passage_time_s"] <= end for row in timeline):
            raise ValueError(f"Accepted same-colour event overlaps prefix: {root}")
        members = [root]
        for row in timeline:
            pid = row["candidate_id"]
            if pid == root or row["event_status"] != "screen_abstention" or \
                    row["candidate_colour"] != proposal["colour"] or \
                    not start <= row["passage_time_s"] <= end:
                continue
            moving = motion_rows.get(pid)
            # A second no-path passage cue may arise in another view while
            # the root stone is observed moving; preserve that mismatch.
            if moving and not moving["selection"].get("path"):
                members.append(pid)
        if claimed.intersection(members):
            raise ValueError("Overlapping shared-prefix episode proposals")
        claimed.update(members)
        episodes.append({
            "episode_id": f"P{index:02d}",
            "status": "partial_observed_travel_review_proposal",
            "root_candidate_id": root,
            "candidate_ids": members,
            "candidate_passage_times_s": {
                pid: by_id[pid]["passage_time_s"] for pid in members},
            "overlapping_passages": [{
                "candidate_id": pid,
                "passage_time_s": by_id[pid]["passage_time_s"],
                "candidate_receiving_view": motion_rows[pid]["receiving_view"],
                "view_matches_observed_prefix":
                    motion_rows[pid]["receiving_view"] == proposal["receiving_view"],
                "separate_supported_path": False,
                "physical_identity_verified": False,
            } for pid in members if pid != root],
            "colour": proposal["colour"],
            "receiving_view": proposal["receiving_view"],
            "observed_interval_s": [start, end],
            "first_ambiguity_time_s": proposal["first_ambiguity_time_s"],
            "prefix_sample_count": proposal["prefix_sample_count"],
            "scored_patch_count": proposal["scored_patch_count"],
            "positive_patch_count": proposal["positive_patch_count"],
            "conditional_endpoint_displacement_m":
                proposal["conditional_endpoint_displacement_m"],
            "observed_receiving_motion": {
                "status": "shared_prefix_only",
                "coordinate_frame": "receiving_camera_view_local_conditional_ice_plane",
                "metric_accuracy_verified": False,
                "samples": [{
                    "source_time_s": point["source_time_s"],
                    "pixel_center": point["pixel_center"],
                    "ground_position_m_conditional": point["ground_position_m"],
                } for point in samples],
                "motion_after_ambiguity_verified": False,
                "inter_camera_identity_verified": False,
            },
            "physical_throw_identity_verified": False,
            "release_time_s": None,
            "physical_settle_time_s": None,
            "post_event_complete_board": None,
            "spin_revolution_count": None,
            "simulation_ready": False,
        })
    mapping = {pid: episode["episode_id"] for episode in episodes
               for pid in episode["candidate_ids"]}
    candidate_rows = [{
        "candidate_id": row["candidate_id"],
        "frozen_event_status": row["event_status"],
        "partial_episode_id": mapping.get(row["candidate_id"]),
        "partial_episode_role": (
            "root" if any(row["candidate_id"] == episode["root_candidate_id"]
                          for episode in episodes) else
            "overlapping_passage" if row["candidate_id"] in mapping else None),
    } for row in timeline]
    return {"episodes": episodes, "candidate_rows": candidate_rows}
