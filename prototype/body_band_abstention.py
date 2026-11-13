"""Development-only low stone-body-support abstention over a frozen screen."""

from collections import Counter


def apply_body_band_abstention(screen, features, threshold=0.5):
    if not 0 < threshold < 1:
        raise ValueError("Neutral-gray threshold must be within (0, 1)")
    decisions = screen["decisions"]
    observed = features["rows"]
    by_id = {row["candidate_id"]: row for row in observed}
    accepted_ids = {row["candidate_id"] for row in decisions if row["accepted"]}
    if (
        len(by_id) != len(observed)
        or len({row["candidate_id"] for row in decisions}) != len(decisions)
        or set(by_id) != accepted_ids
    ):
        raise ValueError("Feature rows must cover every frozen acceptance exactly once")
    derived = []
    flagged = []
    for decision in decisions:
        new = dict(decision)
        pid = decision["candidate_id"]
        if decision["accepted"]:
            feature = by_id[pid]
            fraction = feature["max_neutral_gray_fraction"]
            if fraction is None or fraction < threshold:
                new["accepted"] = False
                new["status"] = (
                    "abstain_body_band_unavailable"
                    if fraction is None
                    else "abstain_low_neutral_stone_body_support"
                )
                flagged.append(pid)
            new["max_neutral_gray_fraction"] = fraction
        derived.append(new)
    retained = {row["candidate_id"] for row in derived if row["accepted"]}
    if not retained.issubset(accepted_ids):
        raise AssertionError("Development stage created an acceptance")
    events = [row for row in screen["events"] if row["id"] in retained]
    if {row["id"] for row in events} != retained:
        raise ValueError("Frozen events do not match accepted decisions")
    return {
        "decisions": derived,
        "events": events,
        "flagged_candidate_ids": flagged,
        "decision_status_counts": dict(Counter(row["status"] for row in derived)),
        "frozen_accepted_count": len(accepted_ids),
        "development_accepted_count": len(retained),
    }
