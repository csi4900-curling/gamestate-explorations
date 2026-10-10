"""Experimental 2024 split-screen confirmation from observed motion extent.

The motion-area threshold is development-fitted on three exposed recordings.
It cannot support a transfer claim until frozen and checked on another source.
"""


def confirm_span_context(events, motion_rows, *, center_x_px=160,
                         half_width_px=60, max_changed_px_80x80=1250,
                         duplicate_window_s=10, duplicate_x_px=30):
    by_id = {row["id"]: row for row in motion_rows}
    ids = [event["id"] for event in events]
    if len(ids) != len(set(ids)) or set(ids) != set(by_id):
        raise ValueError("Candidate and motion IDs must match uniquely")
    ordered = sorted(events, key=lambda event: event["crossing_time_s"])
    decisions = []
    accepted = []
    for event in ordered:
        x = event["crossing_x_px"]
        row = by_id[event["id"]]
        changed = row["changed_px_80x80"]
        if abs(x - center_x_px) > half_width_px:
            status, reason = "unconfirmed", "outside_ice_corridor"
        elif changed > max_changed_px_80x80:
            status, reason = "unconfirmed", "large_surrounding_motion"
        elif any(
            previous["colour"] == event["colour"]
            and previous["view_motion"] == event["view_motion"]
            and event["crossing_time_s"] - previous["crossing_time_s"] < duplicate_window_s
            and abs(x - previous["crossing_x_px"]) < duplicate_x_px
            for previous in accepted
        ):
            status, reason = "unconfirmed", "fragment_of_recent_passage"
        else:
            status, reason = "confirmed", "compact_tracked_motion"
            accepted.append(event)
        decisions.append({"id": event["id"], "status": status, "reason": reason,
                          "changed_px_80x80": changed})
    return decisions
