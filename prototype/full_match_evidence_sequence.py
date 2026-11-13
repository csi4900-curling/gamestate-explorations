"""Ordered candidate evidence, with unknown physical game state kept explicit."""

from collections import Counter, defaultdict


def build_sequence(
    timeline, inventory, context, right_reviews, left_review, rescue=None, rescue_review=None
):
    source = timeline["source_sha256"]
    if any(
        item["source_sha256"] != source
        for item in (inventory, context, left_review, *right_reviews.values())
    ):
        raise ValueError("Source fingerprints differ")
    if rescue is not None and rescue["source_sha256"] != source:
        raise ValueError("Rescue source fingerprint differs")
    if rescue_review is not None and rescue_review["source_sha256"] != source:
        raise ValueError("Rescue review source fingerprint differs")
    left = timeline["observed_events"]
    right = inventory["rows"]
    left_by_id = {item["id"]: item for item in left}
    right_by_id = {item["proposal_id"]: item for item in right}
    if len(left_by_id) != len(left) or len(right_by_id) != len(right):
        raise ValueError("Duplicate candidate ID")
    if (
        len(left) != inventory["left_event_count"]
        or len(right) != inventory["right_proposal_count"]
    ):
        raise ValueError("Inventory counts differ")
    if timeline["supported_runs"] and [
        r["interval_s"] for r in timeline["supported_runs"] if r["layout"] == "split_2024"
    ] != [r["interval_s"] for r in inventory["supported_runs"]]:
        raise ValueError("Supported runs differ")
    if timeline["coverage_gaps_s"] != inventory["coverage_gaps_s"]:
        raise ValueError("Coverage gaps differ")

    context_by_id = {item["proposal_id"]: item for item in context["rows"]}
    if len(context_by_id) != len(context["rows"]) or set(context_by_id) != set(right_by_id):
        raise ValueError("Context must cover each right proposal once")
    reviewed_right = {}
    for run_id, review in right_reviews.items():
        for item in review["rows"]:
            proposal_id = item.get("proposal_id")
            if proposal_id is None:
                proposal_id = f"{run_id}:{item['raw_track_id']}"
            if not proposal_id.startswith(f"{run_id}:"):
                raise ValueError("Reviewed proposal run differs")
            if proposal_id in reviewed_right or proposal_id not in right_by_id:
                raise ValueError("Duplicate or unknown reviewed right proposal")
            reviewed_right[proposal_id] = item["source_prefix_class"]
    reviewed_left = {
        item["left_event_id"]: item["source_prefix_class"] for item in left_review["rows"]
    }
    if len(reviewed_left) != len(left_review["rows"]):
        raise ValueError("Duplicate left source review")
    expected_left_only = set(inventory["left_events_without_any_right_time_colour_candidate"])
    if set(reviewed_left) != expected_left_only:
        raise ValueError("Left-only source review coverage differs")
    expected_right_only = {
        row["proposal_id"]
        for row in right
        if row["temporal_status"] == "no_left_time_colour_candidate"
    }
    if not expected_right_only <= set(reviewed_right):
        raise ValueError("Unreviewed right-only proposal")
    if rescue is not None:
        rescue_by_id = {row["left_event_id"]: row for row in rescue["rows"]}
        if len(rescue_by_id) != len(rescue["rows"]) or set(rescue_by_id) != expected_left_only:
            raise ValueError("Targeted rescue must cover exactly the left-only events")
    else:
        rescue_by_id = {}
    rescue_ids = {
        candidate["raw_track_id"]
        for row in rescue_by_id.values()
        for candidate in row["candidates"]
    }
    if rescue_review is None:
        if rescue_ids:
            raise ValueError("Targeted rescue candidates need source review")
        reviewed_rescue = {}
    else:
        reviewed_rescue = {
            row["raw_track_id"]: row["source_prefix_class"] for row in rescue_review["rows"]
        }
        if len(reviewed_rescue) != len(rescue_review["rows"]) or set(reviewed_rescue) != rescue_ids:
            raise ValueError("Targeted rescue source review coverage differs")

    right_for_left = defaultdict(list)
    for row in right:
        for left_id in row["direction_aware_same_colour_left_ids_within_lag"]:
            event = left_by_id.get(left_id)
            if event is None or event["colour"] != row["colour_claim"]:
                raise ValueError("Invalid temporal left reference")
            right_for_left[left_id].append(row["proposal_id"])
    if {item["id"] for item in left if item["id"] not in right_for_left} != expected_left_only:
        raise ValueError("Inventory left-only list differs from links")

    rows = []
    for event in left:
        event_id = event["id"]
        support_ids = sorted(right_for_left[event_id])
        rescue_row = rescue_by_id.get(event_id)
        rows.append(
            {
                "candidate_id": f"left:{event_id}",
                "observation_time_s": event["crossing_time_s"],
                "observation_kind": "left_tracked_passage",
                "colour_claim": event["colour"],
                "left_event_id": event_id,
                "left_source_pixel_class": reviewed_left.get(event_id),
                "right_temporal_candidate_ids": support_ids,
                "right_temporal_candidate_count": len(support_ids),
                "right_targeted_relaxed_raw_ids": (
                    [candidate["raw_track_id"] for candidate in rescue_row["candidates"]]
                    if rescue_row
                    else []
                ),
                "right_targeted_relaxed_source_classes": (
                    {
                        candidate["raw_track_id"]: reviewed_rescue[candidate["raw_track_id"]]
                        for candidate in rescue_row["candidates"]
                    }
                    if rescue_row
                    else {}
                ),
                "evidence_tier": (
                    "source_reviewed_left_only"
                    if event_id in reviewed_left
                    else "multiple_right_time_colour_candidates"
                    if len(support_ids) > 1
                    else "one_right_time_colour_candidate"
                    if support_ids
                    else "left_provisional"
                ),
            }
        )
    for proposal_id in sorted(expected_right_only):
        proposal = right_by_id[proposal_id]
        rows.append(
            {
                "candidate_id": f"right:{proposal_id}",
                "observation_time_s": proposal["passage_time_s"],
                "observation_kind": "right_observed_motion_passage",
                "colour_claim": proposal["colour_claim"],
                "left_event_id": None,
                "left_source_pixel_class": None,
                "right_temporal_candidate_ids": [proposal_id],
                "right_temporal_candidate_count": 0,
                "right_targeted_relaxed_raw_ids": [],
                "right_targeted_relaxed_source_classes": {},
                "evidence_tier": "source_reviewed_right_only",
            }
        )
    rows.sort(key=lambda row: (row["observation_time_s"], row["candidate_id"]))
    for index, row in enumerate(rows, 1):
        row["sequence_id"] = f"P{index:03d}"
        row["physical_throw_verified"] = False
        row["game_state_after"] = {
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
        "source_sha256": source,
        "supported_runs": inventory["supported_runs"],
        "coverage_gaps_s": inventory["coverage_gaps_s"],
        "left_candidate_count": len(left),
        "right_proposal_count": len(right),
        "right_only_count": len(expected_right_only),
        "left_only_count": len(expected_left_only),
        "sequence_row_count": len(rows),
        "evidence_tier_counts": dict(Counter(row["evidence_tier"] for row in rows)),
        "right_proposals": [
            {
                **row,
                "context_tier": context_by_id[row["proposal_id"]]["context_tier"],
                "source_pixel_class": reviewed_right.get(row["proposal_id"]),
            }
            for row in right
        ],
        "complete_throw_sequence_verified": False,
        "rows": rows,
    }
