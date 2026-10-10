"""Classify adjacent visual-only and travel-view event evidence."""


def classify_travel_predecessors(shots, fused_events, travel_rows):
    """Keep each travel cue and immediate predecessor without asserting identity."""
    ids = [shot["shot_id"] for shot in shots]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate camera shot")
    index = {shot_id: i for i, shot_id in enumerate(ids)}
    events = {event["shot_id"]: event for event in fused_events}
    if len(events) != len(fused_events):
        raise ValueError("Duplicate fused event shot")
    rows = []
    for travel in travel_rows:
        if travel["status"] != "unlocalized_travel_candidate":
            continue
        shot_id = travel["travel_shot_id"]
        if shot_id not in index:
            raise ValueError(f"Unknown travel shot: {shot_id}")
        i = index[shot_id]
        preceding_shot = shots[i - 1] if i else None
        prior = events.get(preceding_shot["shot_id"]) if preceding_shot else None
        if prior and prior["delivery_window_s"] != preceding_shot["interval_s"]:
            raise ValueError(f"Predecessor event window differs: {shot_id}")
        if prior is None:
            status = "no_adjacent_fused_event"
        elif prior["counter_id"] is not None:
            status = "adjacent_event_has_own_counter"
        elif prior["colour"] is None:
            status = "adjacent_visual_colour_unknown"
        elif prior["colour"] == travel["colour"]:
            status = "adjacent_visual_same_colour"
        else:
            status = "adjacent_visual_colour_conflict"
        rows.append(
            {
                "counter_id": travel["counter_id"],
                "counter_colour": travel["colour"],
                "travel_shot_id": shot_id,
                "travel_window_s": travel["observed_travel_window_s"],
                "preceding_shot_id": preceding_shot["shot_id"] if preceding_shot else None,
                "preceding_fused_event": (
                    {
                        "shot_id": prior["shot_id"],
                        "colour": prior["colour"],
                        "colour_status": prior["colour_status"],
                        "counter_id": prior["counter_id"],
                    }
                    if prior
                    else None
                ),
                "relation_status": status,
                "possible_same_physical_throw": status
                in (
                    "adjacent_visual_same_colour",
                    "adjacent_visual_colour_conflict",
                    "adjacent_visual_colour_unknown",
                ),
                "physical_identity_verified": False,
                "merge_applied": False,
            }
        )
    return rows
