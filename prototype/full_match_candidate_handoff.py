"""Merge routed left proposals and camera-aware right-only review evidence."""

from collections import Counter
from copy import deepcopy


def _unique(rows, key):
    index = {row[key]: row for row in rows}
    if len(index) != len(rows):
        raise ValueError(f"Duplicate {key}")
    return index


def build_full_match_candidate_handoff(
    timeline, raw, variant, fusion, partial, activity, reviews=None
):
    if len(timeline["supported_runs"]) != 1:
        raise ValueError("This handoff requires exactly one routed source run")
    source = timeline["source_sha256"]
    for name, artifact in (
        ("raw", raw),
        ("right variant", variant),
        ("fusion", fusion),
        ("partial", partial),
        ("activity", activity),
    ):
        if artifact["source_sha256"] != source:
            raise ValueError(f"{name} source differs")
    accepted = _unique(timeline["observed_events"], "id")
    raw_accepted = _unique(raw["events"], "id")
    withheld = _unique(raw["withheld_events"], "id")
    decisions = _unique(raw["decisions"], "id")
    if len(accepted) != timeline["observed_event_count"]:
        raise ValueError("Timeline event count differs")
    if {row["source_event_id"] for row in accepted.values()} != set(raw_accepted) or len(
        accepted
    ) != len(raw_accepted):
        raise ValueError("Raw accepted IDs differ from routed timeline")
    if set(raw_accepted) & set(withheld) or set(decisions) != (set(raw_accepted) | set(withheld)):
        raise ValueError("Raw screen does not cover all left proposals")
    for row in accepted.values():
        source_row = raw_accepted[row["source_event_id"]]
        if (
            row["colour"] != source_row["colour"]
            or row["crossing_time_s"] != source_row["crossing_time_s"]
            or decisions[source_row["id"]]["status"] != "confirmed"
        ):
            raise ValueError("Accepted left event differs from raw screen")
    for row in withheld.values():
        if decisions[row["id"]]["status"] != "unconfirmed":
            raise ValueError("Withheld left row was confirmed")
    blind = activity["newly_unsupported_intervals"]
    if any(row["reason"] != "left_panel_static_while_right_panel_active" for row in blind):
        raise ValueError("Unknown source-activity exclusion")
    if (
        sum(end - start for row in blind for start, end in [row["interval_s"]])
        != activity["newly_unsupported_seconds"]
    ):
        raise ValueError("Source-activity blind duration differs")
    right = _unique(
        [row for interval in variant["intervals"] for row in interval["entry_review_proposals"]],
        "raw_track_id",
    )
    fused = _unique(fusion["right_entries"], "right_raw_track_id")
    boards = _unique(partial["entries"], "right_raw_track_id")
    if not (
        set(right) == set(fused) == set(boards)
        and len(right) == fusion["right_entry_count"] == partial["right_only_entry_count"]
    ):
        raise ValueError("Right proposal, fusion and partial rows differ")
    rows = []
    for event in timeline["observed_events"]:
        rows.append(
            {
                "candidate_id": f"left:{event['id']}",
                "source_time_s": event["crossing_time_s"],
                "time_semantics": event["time_semantics"],
                "colour_claim": event["colour"],
                "observation_kind": "left_provisional_passage",
                "evidence_tier": "left_screen_confirmed_not_physical_throw",
                "left_screen_reason": decisions[event["source_event_id"]]["reason"],
                "left_coverage_status": "sampled_left_activity_supported",
                "observed_motion": {
                    "track_id": event["track_id"],
                    "crossing_x_px": event["crossing_x_px"],
                    "passage_y_px": event["passage_y_px"],
                },
                "post_candidate_partial_board": None,
            }
        )
    run_id = timeline["supported_runs"][0]["id"]
    for event in raw["withheld_events"]:
        rows.append(
            {
                "candidate_id": f"left:{run_id}-{event['id']}",
                "source_time_s": event["crossing_time_s"],
                "time_semantics": event["time_semantics"],
                "colour_claim": event["colour"],
                "observation_kind": "left_unconfirmed_raw_motion",
                "evidence_tier": "left_screen_abstention_not_event",
                "left_screen_reason": decisions[event["id"]]["reason"],
                "left_coverage_status": "sampled_left_activity_supported",
                "observed_motion": {
                    "track_id": event["track_id"],
                    "crossing_x_px": event["crossing_x_px"],
                    "passage_y_px": event["passage_y_px"],
                },
                "post_candidate_partial_board": None,
            }
        )
    for rid, proposal in right.items():
        link, board = fused[rid], boards[rid]
        time_s = proposal["entry_crossing"]["time_s"]
        if (
            link["right_entry_time_s"] != time_s
            or board["entry_time_s"] != time_s
            or proposal["colour_claim"] != link["right_colour_claim"]
            or link["fusion_status"] != "right_only_left_static_review"
            or link["conditional_left_candidate_id"] is not None
            or not any(a <= time_s < b for item in blind for a, b in [item["interval_s"]])
        ):
            raise ValueError("Right-only passage or blind coverage differs")
        rows.append(
            {
                "candidate_id": f"right:{rid}",
                "source_time_s": time_s,
                "time_semantics": "interpolated_right_image_line_crossing",
                "colour_claim": proposal["colour_claim"],
                "observation_kind": "right_only_review_entry",
                "evidence_tier": "right_motion_prefix_not_physical_throw",
                "left_screen_reason": None,
                "left_coverage_status": "left_static_right_active",
                "observed_motion": {
                    "entry_line_y_px": proposal["entry_line_y_px"],
                    "crossing_x_px": proposal["entry_crossing"]["x_px"],
                    "observed_prefix_interval_s": proposal["observed_prefix_interval_s"],
                    "observed_prefix_points": deepcopy(proposal["observed_prefix_points"]),
                },
                "post_candidate_partial_board": {
                    "status": board["observation_status"],
                    "coordinate_frame": "right_camera_image_pixels",
                    "stable_cap_proposals": deepcopy(board["stable_cap_proposals"]),
                    "complete_board_verified": False,
                },
            }
        )
    if len(rows) != len(raw_accepted) + len(withheld) + len(right):
        raise ValueError("Candidate inventory count differs")
    for row in rows:
        time_s = row["source_time_s"]
        if not any(
            a <= time_s < b for run in timeline["supported_runs"] for a, b in [run["interval_s"]]
        ):
            raise ValueError("Candidate outside routed run")
        if row["observation_kind"].startswith("left_") and any(
            a <= time_s < b for item in blind for a, b in [item["interval_s"]]
        ):
            raise ValueError("Left motion candidate inside static-left interval")
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
    rows.sort(key=lambda row: (row["source_time_s"], row["candidate_id"]))
    ids = [row["candidate_id"] for row in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate merged candidate ID")
    for index, row in enumerate(rows, 1):
        row["sequence_id"] = f"P{index:03d}"
        row["source_pixel_review"] = None
    review_counts = Counter()
    if reviews is not None:
        if reviews["source_sha256"] != source:
            raise ValueError("Source-pixel reviews have another video")
        by_id = {row["candidate_id"]: row for row in rows}
        reviewed = _unique(reviews["reviews"], "candidate_id")
        allowed = {
            "stone_body_at_crossing",
            "person_at_crossing",
            "person_head_at_crossing",
            "person_bending_over_ice_at_crossing",
        }
        for candidate_id, item in reviewed.items():
            if (
                candidate_id not in by_id
                or item["review_source"] not in reviews["review_sources"]
                or item["source_pixel_class"] not in allowed
                or item["physical_throw_verified"] is not False
            ):
                raise ValueError("Invalid source-pixel review")
            row = by_id[candidate_id]
            if (
                abs(row["source_time_s"] - item["source_time_s"]) > 0.001
                or row["colour_claim"] != item["colour_claim"]
            ):
                raise ValueError("Source-pixel review candidate differs")
            row["source_pixel_review"] = {
                "source_pixel_class": item["source_pixel_class"],
                "review_origin": "same_agent_prediction_targeted",
                "sheet_path": reviews["review_sources"][item["review_source"]]["sheet"],
                "physical_throw_verified": False,
            }
            review_counts[item["source_pixel_class"]] += 1
    return {
        "source_id": timeline["source_id"],
        "source_sha256": source,
        "source_interval_s": deepcopy(timeline["source_interval_s"]),
        "routed_supported_runs": deepcopy(timeline["supported_runs"]),
        "routed_coverage_gaps_s": deepcopy(timeline["coverage_gaps_s"]),
        "left_trigger_blind_intervals": deepcopy(blind),
        "candidate_counts_by_kind": dict(Counter(row["observation_kind"] for row in rows)),
        "candidate_count": len(rows),
        "source_pixel_review_counts": dict(review_counts),
        "possible_event_proposal_count": len(accepted) + len(right),
        "complete_throw_sequence_verified": False,
        "ordered_candidates": rows,
        "right_adjacent_partial_cap_transitions": deepcopy(partial["adjacent_transitions"]),
        "limitations": [
            "Candidate counts are not physical throw counts or event precision/recall.",
            "Left raw abstentions are retained for error review, not treated as deliveries.",
            "Right-only entries are image-motion prefixes within left-trigger blind coverage; their colour and temporal order do not verify physical identity.",
            "All boards are partial image-cap observations; no complete game state or simulation-ready event is inferred.",
        ],
    }
