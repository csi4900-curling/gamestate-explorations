"""Ordered full-match event evidence with explicit unknown physical state."""


def build_candidate_sequence(baseline, bridged, bridge_triage, fusion,
                             crossing_review, right_source_review):
    source_hashes = {item["source_sha256"] for item in
                     (baseline, bridged, bridge_triage, fusion,
                      crossing_review, right_source_review)}
    if len(source_hashes) != 1:
        raise ValueError("Source fingerprints differ")
    baseline_events = {row["id"]: row for row in baseline["observed_events"]}
    bridged_events = {row["id"]: row for row in bridged["observed_events"]}
    if (len(baseline_events) != len(baseline["observed_events"])
            or len(bridged_events) != len(bridged["observed_events"])):
        raise ValueError("Duplicate left event ID")
    preserved = bridge_triage["original_candidates_preserved"]
    by_old = {row["original_id"]: row for row in preserved}
    old_by_new = {row["bridged_id"]: row["original_id"] for row in preserved}
    preserved_new_ids = {row["bridged_id"] for row in preserved}
    if (len(by_old) != len(preserved) or set(by_old) != set(baseline_events)
            or len(preserved_new_ids) != len(preserved)
            or not preserved_new_ids <= set(bridged_events)):
        raise ValueError("Bridge lineage does not preserve the distinct baseline candidates")
    for old_id, mapping in by_old.items():
        old = baseline_events[old_id]
        new = bridged_events[mapping["bridged_id"]]
        expected = (mapping["time_s"], mapping["colour"])
        if (old["crossing_time_s"], old["colour"]) != expected or (
                new["crossing_time_s"], new["colour"]) != expected:
            raise ValueError(f"Baseline candidate changed: {old_id}")
    added_ids = set(bridged_events) - preserved_new_ids
    triaged_additions = {row["id"] for row in bridge_triage["new_review_candidates"]}
    if added_ids != triaged_additions or len(triaged_additions) != len(
            bridge_triage["new_review_candidates"]):
        raise ValueError("New bridge candidate lineage differs from triage")
    crossing = {row["candidate_id"]: row for row in crossing_review["rows"]}
    if len(crossing) != len(crossing_review["rows"]) or set(crossing) != added_ids:
        raise ValueError("Crossing review must cover each added bridge candidate")
    reviewed_right = {row["right_raw_track_id"]: row for row in right_source_review["review"]}
    if len(reviewed_right) != len(right_source_review["review"]):
        raise ValueError("Duplicate right source-review ID")

    links = {}
    right_only = []
    right_ids = set()
    for row in fusion["right_entries"]:
        raw_id = row["right_raw_track_id"]
        if raw_id in right_ids:
            raise ValueError("Duplicate right prefix ID")
        right_ids.add(raw_id)
        left_id = row["conditional_left_candidate_id"]
        if left_id is None:
            right_only.append(row)
            continue
        if left_id not in bridged_events or left_id in links:
            raise ValueError("Invalid or duplicate conditional left link")
        if row["fusion_status"] != "cross_view_time_colour_corrob":
            raise ValueError("Linked row lacks corroboration status")
        left = bridged_events[left_id]
        if (row["right_colour_claim"] != left["colour"]
                or row["right_entry_time_s"] <= left["crossing_time_s"]):
            raise ValueError("Right and left colour or chronology disagrees")
        links[left_id] = row
    if not set(reviewed_right) <= right_ids:
        raise ValueError("Source review contains an unknown right prefix")
    if any(row["right_raw_track_id"] not in reviewed_right for row in right_only):
        raise ValueError("Unlinked right prefix lacks source review")

    rows = []
    for event in bridged["observed_events"]:
        event_id = event["id"]
        review = crossing.get(event_id)
        link = links.get(event_id)
        crossing_class = review["crossing_source_class"] if review else None
        if crossing_class == "nonstone_at_tracked_crossing":
            tier = "source_reviewed_nonstone"
        elif crossing_class == "stone_at_tracked_crossing":
            tier = "source_reviewed_stone_with_right" if link else "source_reviewed_stone"
        elif crossing_class == "occluded_identity_uncertain":
            tier = "source_reviewed_occluded"
        elif link:
            tier = "two_view_time_colour_provisional"
        else:
            tier = "left_view_provisional"
        rows.append({
            "candidate_id": event_id,
            "proposal_origin": "baseline_auto_accepted" if event_id in preserved_new_ids
                               else "bridged_gap_review",
            "baseline_candidate_id": old_by_new.get(event_id),
            "observation_time_s": event["crossing_time_s"],
            "observation_kind": "left_tracked_crossing",
            "colour_claim": event["colour"],
            "crossing_source_class": crossing_class,
            "right_entry": ({"raw_track_id": link["right_raw_track_id"],
                             "entry_time_s": link["right_entry_time_s"],
                             "right_minus_left_lag_s": link["right_minus_left_lag_s"],
                             "physical_identity_verified": False} if link else None),
            "evidence_tier": tier,
        })
    for entry in right_only:
        review = reviewed_right[entry["right_raw_track_id"]]
        right_class = review["sampled_prefix_class"]
        if right_class not in ("moving_stone", "moving_person_wheelchair"):
            raise ValueError(f"Unknown right source class: {right_class}")
        rows.append({
            "candidate_id": entry["right_raw_track_id"],
            "proposal_origin": "right_only_prefix",
            "observation_time_s": entry["right_entry_time_s"],
            "observation_kind": "right_entry_crossing",
            "colour_claim": entry["right_colour_claim"],
            "crossing_source_class": right_class,
            "right_entry": {"raw_track_id": entry["right_raw_track_id"],
                            "entry_time_s": entry["right_entry_time_s"],
                            "right_minus_left_lag_s": None,
                            "physical_identity_verified": False},
            "evidence_tier": ("source_reviewed_nonstone" if right_class ==
                              "moving_person_wheelchair" else "right_view_provisional"),
        })
    rows.sort(key=lambda row: (row["observation_time_s"], row["candidate_id"]))
    for index, row in enumerate(rows, 1):
        row["sequence_proposal_id"] = f"P{index:03d}"
        row["game_state_after"] = {
            "physical_throw_verified": False,
            "end_identity": None,
            "official_shot_identity": None,
            "release_time_s": None,
            "settle_time_s": None,
            "complete_board": None,
            "persistent_stone_ids": None,
            "metric_trajectory": None,
            "spin_revolution_count": None,
            "simulation_ready": False,
        }
    return {
        "candidate_sequence_count": len(rows),
        "left_candidate_count": len(bridged_events),
        "baseline_left_count": len(baseline_events),
        "bridged_addition_count": len(added_ids),
        "conditional_two_view_link_count": len(links),
        "right_only_count": len(right_only),
        "evidence_tier_counts": {tier: sum(row["evidence_tier"] == tier for row in rows)
                                 for tier in sorted({row["evidence_tier"] for row in rows})},
        "complete_throw_sequence_verified": False,
        "rows": rows,
    }
