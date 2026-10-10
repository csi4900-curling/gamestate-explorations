"""Keep routed events and unsupported-gap evidence in one candidate ledger."""


def build_gap_candidate_ledger(timeline, inventory, visual=None):
    if (timeline["source_id"] != inventory["source_id"] or
            timeline["source_sha256"] != inventory["source_sha256"] or
            timeline["source_interval_s"] != inventory["source_interval_s"] or
            timeline["coverage_gaps_s"] != inventory["coverage_gaps_s"]):
        raise ValueError("Timeline and gap inventory differ")
    if visual and (visual["source_id"] != timeline["source_id"] or
                   visual["source_sha256"] != timeline["source_sha256"] or
                   visual["source_interval_s"] != timeline["source_interval_s"]):
        raise ValueError("Visual gap source differs")
    gaps = timeline["coverage_gaps_s"]
    runs = [run["interval_s"] for run in timeline["supported_runs"]]
    rows = []
    for event in timeline["observed_events"]:
        t = event["crossing_time_s"]
        if not any(a <= t < b for a, b in runs):
            raise ValueError("Routed event outside supported run")
        rows.append({
            "evidence_id": f"routed:{event['id']}",
            "source_event_id": event["id"],
            "evidence_kind": "supported_route_event_proposal",
            "coverage_status": "supported_route",
            "observation_time_s": t,
            "evidence_interval_s": event["evidence_interval_s"],
            "colour_claim": event["colour"],
            "gap_interval_s": None,
            "nearby_counter_gap_ids": [],
            "distinct_physical_throw_verified": False,
            "simulation_ready": False,
        })
    for field, kind in (("interior_gap_candidates", "counter_inside_unknown_route"),
                        ("boundary_ambiguous", "counter_crosses_route_boundary")):
        for item in inventory[field]:
            a, b = item["gap_interval_s"]
            if [a, b] not in gaps:
                raise ValueError("Counter candidate refers to unknown gap")
            start, end = item["counter_evidence_interval_s"]
            t = item["counter_update_s"]
            if not start <= t <= end:
                raise ValueError("Counter update outside evidence interval")
            if kind == "counter_inside_unknown_route":
                if not a <= start <= end < b:
                    raise ValueError("Interior counter candidate crosses gap boundary")
            elif end < a or start >= b or a <= start and end < b:
                raise ValueError("Boundary counter evidence does not cross route")
            rows.append({
                "evidence_id": f"counter-gap:{item['counter_id']}",
                "source_event_id": item["counter_id"],
                "evidence_kind": kind,
                "coverage_status": ("unknown_route" if kind ==
                                    "counter_inside_unknown_route" else
                                    "route_boundary_ambiguous"),
                "observation_time_s": t,
                "evidence_interval_s": [start, end],
                "colour_claim": item["colour"],
                "gap_interval_s": [a, b],
                "remaining_before": item["remaining_before"],
                "remaining_after": item["remaining_after"],
                "nearby_counter_gap_ids": [],
                "distinct_physical_throw_verified": False,
                "simulation_ready": False,
            })
    if visual:
        for item in visual["motion_candidates"]:
            t = item["crossing_time_s"]
            matched_gaps = [[a, b] for a, b in gaps if a <= t < b]
            if len(matched_gaps) != 1:
                raise ValueError("Visual gap motion outside one unknown route")
            gap = matched_gaps[0]
            if not gap[0] <= item["evidence_interval_s"][0] <= \
                    item["evidence_interval_s"][1] < gap[1]:
                raise ValueError("Visual motion interval leaves unknown route")
            nearby = [row["source_event_id"] for row in rows
                      if row["evidence_kind"] == "counter_inside_unknown_route"
                      and row["gap_interval_s"] == gap
                      and row["colour_claim"] == item["colour"]
                      and abs(row["observation_time_s"] - t) <= 20]
            rows.append({
                "evidence_id": f"visual-gap:{item['id']}",
                "source_event_id": item["id"],
                "evidence_kind": "visual_motion_inside_unknown_route",
                "coverage_status": "unknown_route",
                "observation_time_s": t,
                "evidence_interval_s": item["evidence_interval_s"],
                "colour_claim": item["colour"],
                "gap_interval_s": gap,
                "nearby_counter_gap_ids": nearby,
                "counter_visual_physical_identity_verified": False,
                "distinct_physical_throw_verified": False,
                "simulation_ready": False,
            })
    ids = [row["evidence_id"] for row in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate evidence ID")
    rows.sort(key=lambda row: (row["observation_time_s"], row["evidence_id"]))
    for i, row in enumerate(rows, 1):
        row["sequence_id"] = f"P{i:03d}"
    return rows
