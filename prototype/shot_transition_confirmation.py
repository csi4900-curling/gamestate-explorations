"""Corroborate a delivery-looking shot with same-colour motion after a cut.

This is two-shot visual evidence, not proof of physical stone identity or an
exact release. Ambiguous colours stay ambiguous.
"""


def confirm_shot_transitions(predictions, motion_audits):
    """Return one explicit decision for each shot-origin prediction.

    Motion audits may come from different object-proposal channels. A channel
    supports a colour only if it has a sustained track in both the candidate
    shot and its immediately following shot.
    """
    if not motion_audits:
        raise ValueError("At least one motion audit is required")
    shot_ids = [row["shot_id"] for row in predictions]
    if len(shot_ids) != len(set(shot_ids)):
        raise ValueError("Duplicate shot-origin prediction")
    by_channel = []
    for channel, rows in motion_audits.items():
        indexed = {row["shot_id"]: row for row in rows}
        if len(indexed) != len(rows) or set(indexed) != set(shot_ids):
            raise ValueError(f"Shot ID mismatch in {channel} motion audit")
        by_channel.append((channel, indexed))
    decisions = []
    for prediction in predictions:
        shot_id = prediction["shot_id"]
        support = []
        for channel, rows in by_channel:
            row = rows[shot_id]
            same = {item["colour"] for item in row["same_shot_candidates"]}
            following = {item["colour"] for item in row["following_shot_candidates"]}
            support.extend({"channel": channel, "colour": colour}
                           for colour in sorted(same & following))
        colours = sorted({row["colour"] for row in support})
        if not prediction["predicted"]:
            status, reason = "unconfirmed", "shot_origin_not_predicted"
        elif not support:
            status, reason = "unconfirmed", "no_same_colour_two_shot_motion"
        else:
            status, reason = "corroborated_candidate", "two_shot_colour_motion"
        decisions.append({"shot_id": shot_id, "status": status, "reason": reason,
                          "supported_colours": colours,
                          "colour": colours[0] if len(colours) == 1 else None,
                          "colour_status": "unique" if len(colours) == 1 else
                          "ambiguous" if colours else "unsupported",
                          "channel_support": support})
    return decisions
