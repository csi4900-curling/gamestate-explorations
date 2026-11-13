"""Postscore rescue of a weak origin score with two-channel shot motion."""


def rescue_weak_origins(origins, decisions, *, min_origin_probability=0.2):
    """Rescue only unique cross-channel colour agreement, retaining provenance."""
    by_id = {row["shot_id"]: row for row in decisions}
    if len(by_id) != len(decisions) or set(by_id) != {row["shot_id"] for row in origins}:
        raise ValueError("Origin/decision shot IDs differ")
    result = []
    for origin in origins:
        decision = by_id[origin["shot_id"]]
        support = decision["channel_support"]
        cap = {row["colour"] for row in support if row["channel"] == "cap"}
        learned = {row["colour"] for row in support if row["channel"] == "learned"}
        agreement = sorted(cap & learned)
        eligible = (
            not origin["predicted"]
            and origin["phase_supported"]
            and origin["probability"] >= min_origin_probability
            and len(agreement) == 1
            and (len(cap) == 1 or len(learned) == 1)
        )
        if decision["status"] == "corroborated_candidate":
            status, reason = "corroborated_candidate", "unchanged_two_shot_evidence"
        elif eligible:
            status, reason = "rescued_candidate", "weak_origin_with_two_channel_colour_agreement"
        else:
            status, reason = "unconfirmed", decision["reason"]
        result.append(
            {
                "shot_id": origin["shot_id"],
                "status": status,
                "reason": reason,
                "rescued_colour": agreement[0] if eligible else None,
                "cap_colours": sorted(cap),
                "learned_colours": sorted(learned),
                "origin_probability": origin["probability"],
            }
        )
    return result
