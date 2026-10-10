"""Join broadcast end-display observations without assigning physical ends."""


def attach_display_context(handoff, context):
    timeline = handoff["timeline"]
    events = context["events"]
    by_id = {row["event_id"]: row for row in events}
    if (len(by_id) != len(events) or
            set(by_id) != {row["candidate_id"] for row in timeline} or
            len(timeline) != len(events)):
        raise ValueError("Display context does not cover the handoff candidates")
    output = []
    for row in timeline:
        if row["end_identity"] is not None or row["simulation_ready"]:
            raise ValueError("Expected unresolved physical end and simulation state")
        display = by_id[row["candidate_id"]]
        if display["crossing_time_s"] != row["passage_time_s"] or (
                display["physical_end"] is not None):
            raise ValueError("Display observation conflicts with candidate time or end")
        output.append({**row, "broadcast_end_display": {
            "status": display["display_context_status"],
            "displayed_end": display["displayed_end"],
            "left_marker": display["left_marker"],
            "right_marker": display["right_marker"],
            "physical_end_verified": False,
        }})
    return output
