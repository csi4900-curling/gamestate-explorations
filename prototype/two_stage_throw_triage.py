"""Lossless proposal-to-confirmation handoff for throw-event review.

Existing gates may promote proposals, but a gate's negative decision is not
proof that no throw happened. Preserve each proposal and its evidence so recall
can be audited before uncertain cases are resolved.
"""

from collections import Counter


def _unique_ids(rows, label):
    ids = [row["id"] for row in rows]
    if len(ids) != len(set(ids)):
        raise ValueError(f"Duplicate IDs in {label}")
    return set(ids)


def triage_candidates(proposals, stages):
    """Apply ordered gates without dropping or relabelling raw proposals.

    Each stage is (name, artifact). Its accepted and withheld lists must
    partition the proposals reaching that stage. A withheld proposal remains
    in the review queue; later stages need not have inspected it.
    """
    raw_ids = _unique_ids(proposals, "proposals")
    if not stages:
        raise ValueError("At least one confirmation stage is required")
    active = set(raw_ids)
    evidence = {event_id: [] for event_id in raw_ids}
    names = set()
    for name, artifact in stages:
        if name in names:
            raise ValueError(f"Duplicate stage: {name}")
        names.add(name)
        accepted = _unique_ids(artifact["events"], f"{name} accepted")
        withheld = _unique_ids(artifact["withheld_events"], f"{name} withheld")
        if accepted & withheld or accepted | withheld != active:
            raise ValueError(f"{name} does not partition its input candidates")
        reasons = {row["id"]: row["reason"] for row in artifact.get("decisions", [])}
        if reasons and set(reasons) != active:
            raise ValueError(f"{name} decision IDs differ from input")
        if not reasons and "screened_events" in artifact:
            reasons = {row["id"]: row["status"] for row in artifact["screened_events"]}
            if set(reasons) != active:
                raise ValueError(f"{name} screened IDs differ from input")
        for event_id in sorted(active):
            evidence[event_id].append({
                "stage": name,
                "decision": "supported" if event_id in accepted else "needs_review",
                "reason": reasons.get(event_id),
            })
        active = accepted
    rows = []
    for proposal in proposals:
        event_id = proposal["id"]
        rows.append({
            "id": event_id,
            "crossing_time_s": proposal["crossing_time_s"],
            "colour": proposal["colour"],
            "disposition": "auto_confirmed_candidate" if event_id in active else "needs_review",
            "stage_evidence": evidence[event_id],
            "release_time_s": None,
        })
    counts = Counter(row["disposition"] for row in rows)
    return {
        "proposals": rows,
        "auto_confirmed_events": [p for p in proposals if p["id"] in active],
        "review_events": [p for p in proposals if p["id"] not in active],
        "counts": {
            "proposed": len(rows),
            "auto_confirmed": counts["auto_confirmed_candidate"],
            "needs_review": counts["needs_review"],
        },
    }
