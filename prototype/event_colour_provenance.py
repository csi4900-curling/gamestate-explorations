"""Expose how a fused event obtained its stone colour."""


def annotate_event_colours(events, decisions, counter_alignments):
    """Annotate existing events without changing event identities or colours."""
    by_decision = {row["shot_id"]: row for row in decisions}
    by_counter = {row["counter_id"]: row for row in counter_alignments}
    if len(by_decision) != len(decisions) or len(by_counter) != len(counter_alignments):
        raise ValueError("Duplicate decision shot or counter ID")
    output = []
    for event in events:
        shot_id = event["shot_id"]
        if shot_id not in by_decision:
            raise ValueError(f"Missing visual decision for {shot_id}")
        decision = by_decision[shot_id]
        visual = decision["status"] == "corroborated_candidate"
        visual_colours = list(decision["supported_colours"]) if visual else []
        unique_visual = (decision["colour"] if visual and
                         decision["colour_status"] == "unique" else None)
        counter_id = event["counter_id"]
        counter = by_counter.get(counter_id) if counter_id else None
        if counter_id and (counter is None or counter["shot_id"] != shot_id):
            raise ValueError(f"Counter association mismatch for {shot_id}")
        counter_colour = counter["colour"] if counter else None
        rescue = "weak_origin_and_dual_motion" in event["evidence_sources"]
        if unique_visual and counter_colour and unique_visual != counter_colour:
            basis = "visual_counter_conflict"
            expected = None
        elif unique_visual and counter_colour:
            basis = "visual_and_counter_agree"
            expected = unique_visual
        elif unique_visual:
            basis = "visual_only"
            expected = unique_visual
        elif counter_colour and visual:
            basis = "counter_with_ambiguous_visual"
            expected = counter_colour
        elif counter_colour:
            basis = "counter_without_corroborated_visual"
            expected = counter_colour
        elif rescue:
            basis = "weak_motion_rescue"
            expected = event["colour"]
        elif visual:
            basis = "unresolved_ambiguous_visual"
            expected = None
        else:
            raise ValueError(f"Event {shot_id} has no colour evidence route")
        if event["colour"] != expected:
            raise ValueError(f"Fused colour contradicts evidence for {shot_id}")
        enriched = dict(event)
        enriched["colour_provenance"] = {
            "basis": basis,
            "visual_supported_colours": visual_colours,
            "visual_unique_colour": unique_visual,
            "counter_id": counter_id,
            "counter_colour": counter_colour,
            "resolved_colour": event["colour"],
            "counter_is_delayed_proxy": bool(counter),
        }
        output.append(enriched)
    return output
