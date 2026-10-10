"""Select source shots that need the slower learned-box motion channel."""


def selected_shot_indices(origins, counter_alignments, cap_decisions, fused_events):
    """Include unresolved counter windows, weak origins and visual-only events.

    Each selected shot's immediate successor is scanned for adjacent motion.
    Labels are deliberately absent from this selection.
    """
    by_id = {row["shot_id"]: index for index, row in enumerate(origins)}
    decisions = {row["shot_id"]: row for row in cap_decisions}
    if len(by_id) != len(origins) or set(by_id) != set(decisions):
        raise ValueError("Origin and cap decision shot IDs differ")
    selected = set()
    for counter in counter_alignments:
        if counter["shot_id"] is not None:
            continue
        update = counter["counter_update_s"]
        selected.update(index for index, row in enumerate(origins)
                        if row["interval_s"][0] <= update
                        and row["interval_s"][1] >= update - 45)
    for index, origin in enumerate(origins):
        if (.2 <= origin["probability"] < .5 and origin["phase_supported"]
                and decisions[origin["shot_id"]]["channel_support"]):
            selected.add(index)
    for event in fused_events:
        if event["counter_id"] is None:
            selected.add(by_id[event["shot_id"]])
    selected.update(index + 1 for index in tuple(selected)
                    if index + 1 < len(origins))
    return sorted(selected)
