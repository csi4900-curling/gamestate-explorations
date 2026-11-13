"""Screen order-only counter proposals with source-only post-cut colour cues."""


def screen_order_proposals(order_proposals, postcut_rows):
    """Return colour compatibility without turning an option into an event.

    A post-cut track is evidence, not proof of persistent stone identity. A
    missing or conflicting cue must abstain; even a matching cue is unverified.
    """
    by_shot = {row["shot_id"]: row for row in postcut_rows}
    if len(by_shot) != len(postcut_rows):
        raise ValueError("Duplicate post-cut shot ID")
    output = []
    for proposal in order_proposals:
        shot_id = proposal["proposed_shot_id"]
        if shot_id is None:
            continue
        cue = by_shot.get(shot_id)
        visual_colour = cue["postcut_colour"] if cue is not None else None
        if cue is None:
            status = "not_in_visual_only_sidecar"
        elif visual_colour is None:
            status = "visual_colour_abstained"
        elif visual_colour != proposal["counter_colour"]:
            status = "visual_colour_conflict"
        else:
            status = "colour_compatible_identity_unverified"
        output.append(
            {
                "counter_id": proposal["counter_id"],
                "shot_id": shot_id,
                "counter_colour": proposal["counter_colour"],
                "postcut_colour": visual_colour,
                "postcut_status": cue["postcut_status"] if cue else None,
                "screen_status": status,
                "safe_to_auto_link": False,
            }
        )
    return output
