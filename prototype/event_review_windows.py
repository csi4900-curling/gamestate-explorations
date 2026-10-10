"""Build event-centred review windows without asserting physical shot boundaries."""

import math


def build_review_windows(events, source_interval_s, *, before_s=20.0, after_s=45.0):
    lo, hi = source_interval_s
    if not all(math.isfinite(x) for x in (lo, hi, before_s, after_s)):
        raise ValueError("Non-finite interval or context")
    if not lo < hi or before_s < 0 or after_s < 0:
        raise ValueError("Invalid source interval or context")
    ids = [e["id"] for e in events]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate event ID")
    prepared = []
    for event in events:
        if event.get("colour") not in ("red", "yellow"):
            raise ValueError("Unknown stone colour")
        evidence = event.get("evidence_interval_s")
        if evidence is None:
            t = event["crossing_time_s"]
            evidence = [t, t]
        if len(evidence) != 2:
            raise ValueError("Invalid evidence interval")
        a, b = evidence
        if not all(math.isfinite(x) for x in (a, b)) or not lo <= a <= b < hi:
            raise ValueError("Event evidence outside source interval")
        prepared.append((a, b, event))
    prepared.sort(key=lambda row: (row[0], row[1]))
    windows = []
    for a, b, event in prepared:
        start = max(lo, a - before_s)
        end = min(hi, b + after_s)
        windows.append(
            {
                "event_id": event["id"],
                "colour": event["colour"],
                "review_start_s": start,
                "review_end_s": end,
                "core_evidence_interval_s": [a, b],
                "evidence_kind": event.get("evidence_kind"),
                "physical_start_s": None,
                "physical_end_s": None,
                "status": "provisional_event_review_window",
            }
        )
    return {
        "review_windows": windows,
        "source_interval_s": [lo, hi],
        "context_s": {"before": before_s, "after": after_s},
        "limitations": [
            "Windows can overlap; they are review contexts, not a partition of the game.",
            "Counter evidence may appear after delivery, and visual evidence may start after release.",
            "No physical throw start, completion, trajectory or settled board is inferred.",
        ],
    }
