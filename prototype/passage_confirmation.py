"""Experimental same-layout evidence screen for bidirectional passages.

This is a candidate rule fitted on exposed 2024 split-screen development clips.
It must be frozen and tested on a new recording before any transfer claim.
"""

import math


def confirm_passages(events, *, min_positive_speed=14.8, min_negative_speed=18.0,
                     duplicate_window_s=15.0, phase_neighbor_s=90.0):
    """Return every candidate with a confirmation status and explicit reason."""
    if len({event["id"] for event in events}) != len(events):
        raise ValueError("Duplicate event IDs")
    ordered = sorted(events, key=lambda event: event["crossing_time_s"])
    results = []
    for event in ordered:
        speed = event["velocity_px_s"][1]
        direction = event["view_motion"]
        if not math.isfinite(speed):
            raise ValueError(f"Invalid velocity for {event['id']}")
        if direction not in ("positive_y", "negative_y"):
            raise ValueError(f"Invalid direction for {event['id']}")
        threshold = min_positive_speed if direction == "positive_y" else min_negative_speed
        if abs(speed) < threshold:
            status, reason = "unconfirmed", "below_layout_motion_speed"
        else:
            status, reason = "confirmed", "motion_speed_supported"
        results.append({"id": event["id"], "status": status, "reason": reason})

    # Competing passages within one delivery cycle remain in evidence. The
    # stronger motion trace wins provisionally; a tie favours the earlier one.
    for i, event in enumerate(ordered):
        if results[i]["status"] != "confirmed":
            continue
        competitors = [
            j for j, other in enumerate(ordered)
            if j != i and results[j]["status"] == "confirmed"
            and abs(other["crossing_time_s"] - event["crossing_time_s"]) < duplicate_window_s
        ]
        if any(
            (abs(ordered[j]["velocity_px_s"][1]), -ordered[j]["crossing_time_s"])
            > (abs(event["velocity_px_s"][1]), -event["crossing_time_s"])
            for j in competitors
        ):
            results[i].update(status="unconfirmed", reason="competing_passage")

    # An isolated reversed trace bracketed by two same-direction passages is
    # ambiguous in a fixed split-screen view; do not confirm it as a delivery.
    for i, event in enumerate(ordered):
        if results[i]["status"] != "confirmed":
            continue
        earlier = [j for j in range(i) if results[j]["status"] == "confirmed"
                   and event["crossing_time_s"] - ordered[j]["crossing_time_s"] <= phase_neighbor_s]
        later = [j for j in range(i + 1, len(ordered)) if results[j]["status"] == "confirmed"
                 and ordered[j]["crossing_time_s"] - event["crossing_time_s"] <= phase_neighbor_s]
        if earlier and later and (ordered[earlier[-1]]["view_motion"]
                                  == ordered[later[0]]["view_motion"]
                                  != event["view_motion"]):
            results[i].update(status="unconfirmed", reason="isolated_camera_direction")
    return results
