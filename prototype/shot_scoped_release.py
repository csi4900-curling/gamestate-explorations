"""Accept held-to-motion passages only in an event's declared origin shot."""


def select_event_release(event, broad_scan, shots_by_id, held_scans=None):
    """Return a scoped cue decision without inferring cross-camera stone identity."""
    held_scans = held_scans or {}
    kind = event["candidate_class"]
    if kind in ("visual_origin_existing", "counter_linked_held_origin_provisional"):
        held = event.get("attached_held_evidence") or {}
        shot_id = held.get("shot_id") if kind == "counter_linked_held_origin_provisional" else None
        shot_id = shot_id or event["source_shot_ids"][0]
        scan = broad_scan
        route = "existing_single_shot_window"
    elif kind == "counter_linked_travel_only_provisional":
        held = event.get("attached_held_evidence") or {}
        shot_id = held.get("shot_id")
        if not shot_id:
            return {"scope_status": "no_attached_origin_shot", "origin_shot_id": None,
                    "scope_route": "abstain", "passages": [],
                    "unique_release_cue_s": None, "unique_passage_colour": None}
        if event["event_id"] not in held_scans:
            raise ValueError(f"Missing held-shot rescan: {event['event_id']}")
        scan = held_scans[event["event_id"]]["scoped_scan"]
        if held_scans[event["event_id"]]["held_shot_id"] != shot_id:
            raise ValueError("Held-shot rescan ID mismatch")
        route = "attached_held_shot_rescan"
    else:
        raise ValueError(f"Unknown candidate class: {kind}")
    if shot_id not in event["source_shot_ids"] or shot_id not in shots_by_id:
        raise ValueError("Origin shot is not declared by event")
    shot_start, shot_end = shots_by_id[shot_id]
    start, end = (event["delivery_window_s"] if route == "existing_single_shot_window"
                  else held_scans[event["event_id"]]["held_shot_interval_s"])
    if not shot_start <= start < end <= shot_end:
        raise ValueError("Release scan extends outside declared origin shot")
    if route == "existing_single_shot_window" and broad_scan["delivery_window_s"] != [start, end]:
        raise ValueError("Existing release scan window differs from event")
    passages = scan["passages"]
    for passage in passages:
        if not (start <= passage["held_interval_s"][0]
                <= passage["release_cue_s"]
                <= passage["moving_interval_s"][1] < end):
            raise ValueError("Release passage crosses scoped camera-shot boundary")
    cue = passages[0] if len(passages) == 1 else None
    return {"scope_status": "unique_passage" if cue else "no_unique_passage",
            "origin_shot_id": shot_id, "scope_route": route,
            "scanned_interval_s": [start, end], "passages": passages,
            "unique_release_cue_s": cue["release_cue_s"] if cue else None,
            "unique_passage_colour": cue["colour"] if cue else None}
