"""Join event, motion and board evidence without promoting it to game truth."""


def build_evidence_handoff(candidates, screen, motion, boards, comparisons):
    event_rows = candidates["events"] + candidates["withheld_events"]
    by_id = {row["id"]: row for row in event_rows}
    if len(by_id) != len(event_rows):
        raise ValueError("Duplicate passage candidate ID")
    decision_rows = screen["decisions"]
    decisions = {row["candidate_id"]: row for row in decision_rows}
    motion_rows = {row["candidate_id"]: row for row in motion["rows"]}
    accepted = {row["candidate_id"] for row in decision_rows if row["accepted"]}
    board_rows = {row["candidate_id"]: row for row in boards["rows"]}
    comparison_rows = {row["after_candidate_id"]: row for row in comparisons["comparisons"]}
    if (
        len(decisions) != len(decision_rows)
        or len(motion_rows) != len(motion["rows"])
        or len(board_rows) != len(boards["rows"])
        or len(comparison_rows) != len(comparisons["comparisons"])
    ):
        raise ValueError("Duplicate evidence ID")
    if (
        set(decisions) != {row["id"] for row in candidates["events"]}
        or set(motion_rows) != set(decisions)
        or set(board_rows) != accepted
        or set(comparison_rows) != accepted - {boards["rows"][0]["candidate_id"]}
    ):
        raise ValueError("Evidence IDs do not form the expected coverage")
    output = []
    for event in sorted(event_rows, key=lambda row: row["crossing_time_s"]):
        pid = event["id"]
        decision = decisions.get(pid)
        status = (
            "provisional_event"
            if decision and decision["accepted"]
            else "screen_abstention"
            if decision
            else "outside_screen_corridor"
        )
        item = {
            "candidate_id": pid,
            "event_status": status,
            "candidate_colour": event["colour"],
            "passage_time_s": event["crossing_time_s"],
            "passage_time_semantics": event["time_semantics"],
            "candidate_evidence_kind": event["evidence_kind"],
            "screen_decision": decision["status"] if decision else None,
            "physical_throw_identity_verified": False,
            "release_time_s": None,
            "physical_settle_time_s": None,
            "spin_revolution_count": None,
            "end_identity": None,
            "complete_game_state": False,
            "simulation_ready": False,
        }
        if status == "provisional_event":
            moving = motion_rows[pid]
            board = board_rows[pid]
            path = moving["selection"].get("path") or []
            if (
                not path
                or moving["receiving_view"] != board["receiving_view"]
                or board["crossing_time_s"] != event["crossing_time_s"]
            ):
                raise ValueError(f"Inconsistent accepted event evidence: {pid}")
            item["receiving_view"] = moving["receiving_view"]
            item["observed_receiving_motion"] = {
                "status": moving["selection"]["status"],
                "coordinate_frame": "receiving_camera_view_local_conditional_ice_plane",
                "metric_accuracy_verified": False,
                "samples": [
                    {
                        "source_time_s": sample["source_time_s"],
                        "pixel_center": sample["pixel_center"],
                        "ground_position_m_conditional": sample["ground_position_m"],
                    }
                    for sample in path
                ],
                "inter_camera_identity_verified": False,
            }
            item["post_event_partial_board"] = {
                "status": board["board"]["status"],
                "tail_interval_s": [board["tail"]["start_s"], board["tail"]["stop_s"]]
                if board["tail"]["eligible"]
                else None,
                "registered_frame_count": board["registered_frame_count"],
                "registration_abstention_count": board["registration_abstention_count"],
                "coordinate_frame": board["coordinate_frame"],
                "stones": board["board"]["stones"],
                "completeness": board["completeness"],
                "settle_verified": board["post_throw_settle_verified"],
            }
            item["comparison_from_previous_accepted_event"] = comparison_rows.get(pid)
        output.append(item)
    return output
