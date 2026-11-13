"""Build review intervals from appearance-screened passage candidates.

Intervals end at the next candidate passage. They are not physical shot endings.
"""

from throw_segmentation import review_segments


def build_segments(events, screening, source_start, source_end):
    if len({e["id"] for e in events}) != len(events):
        raise ValueError("Duplicate raw event ID")
    results = screening["events"]
    by_id = {row["id"]: row for row in results}
    if len(by_id) != len(results) or set(by_id) != {e["id"] for e in events}:
        raise ValueError("Screening must cover every raw event exactly once")
    accepted = []
    withheld = []
    for event in events:
        evidence = by_id[event["id"]]
        if (
            event["crossing_time_s"] != evidence["crossing_time_s"]
            or event["colour"] != evidence["colour"]
        ):
            raise ValueError("Screening was built from different events")
        status = evidence["appearance"]["status"]
        if status == "stone_appearance_candidate":
            accepted.append(event)
        elif status in ("person_or_other_object_suspected", "appearance_unavailable"):
            withheld.append(
                {"id": event["id"], "crossing_time_s": event["crossing_time_s"], "reason": status}
            )
        else:
            raise ValueError("Unknown appearance status")
    segments = review_segments(accepted, source_start, source_end)
    for row in segments:
        row.update(status="provisional_review_interval", physical_end_s=None)
    return {
        "segments": segments,
        "withheld_candidates": withheld,
        "unassigned_prefix_s": [source_start, segments[0]["start_s"]]
        if segments
        else [source_start, source_end],
        "limitations": [
            "Appearance screening is unvalidated on unseen recordings; a withheld candidate can be a real throw.",
            "Boundary at the next candidate is for review, not physical completion.",
            "A false or missed event can corrupt adjacent review intervals.",
        ],
    }
