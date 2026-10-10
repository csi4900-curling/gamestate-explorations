"""Join independent within-view and receiving-view colour observations."""


def join_source_colour(release_rows, postcut_rows):
    """Preserve agreement/abstention per release-cue event without event mutation."""
    postcut = {row["shot_id"]: row for row in postcut_rows}
    if len(postcut) != len(postcut_rows):
        raise ValueError("Duplicate post-cut shot ID")
    result = []
    seen_events = set()
    for event in release_rows:
        event_id = event["event_id"]
        if event_id in seen_events:
            raise ValueError("Duplicate release event ID")
        seen_events.add(event_id)
        if event["unique_passage_colour"] is None:
            continue
        origin_shot = event["source_shot_ids"][0]
        sidecar = postcut.get(origin_shot)
        receiving_colour = (sidecar["postcut_colour"] if sidecar and
                            sidecar["postcut_status"] == "unique_strict_postcut_motion"
                            else None)
        passage_colour = event["unique_passage_colour"]
        if sidecar is None:
            status = "receiving_view_not_scanned"
        elif receiving_colour is None:
            status = "receiving_view_abstained"
        elif receiving_colour != passage_colour:
            status = "source_cues_conflict"
        else:
            status = "source_colour_concordant_identity_unverified"
        source_colour = passage_colour if status.startswith("source_colour_concordant") else None
        ledger_colour = event["ledger_colour"]
        result.append({
            "event_id": event_id,
            "origin_shot_id": origin_shot,
            "counter_id": event["counter_id"],
            "ledger_colour": ledger_colour,
            "passage_colour": passage_colour,
            "release_cue_s": event["unique_release_cue_s"],
            "postcut_colour": receiving_colour,
            "postcut_status": sidecar["postcut_status"] if sidecar else None,
            "source_colour": source_colour,
            "status": status,
            "ledger_relation": ("source_colour_unresolved" if source_colour is None else
                                "ledger_unknown" if ledger_colour is None else
                                "agrees_with_ledger" if source_colour == ledger_colour else
                                "conflicts_with_ledger"),
            "physical_stone_identity_verified": False,
            "simulation_ready": False,
        })
    return result
