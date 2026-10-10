"""Audit delayed-counter shot options against linked broadcast-shot order."""


def shot_number(shot_id):
    if not shot_id.startswith("S") or not shot_id[1:].isdigit():
        raise ValueError(f"Invalid shot ID: {shot_id}")
    return int(shot_id[1:])


def counter_number(counter_id):
    if not counter_id.startswith("B") or not counter_id[1:].isdigit():
        raise ValueError(f"Invalid counter ID: {counter_id}")
    return int(counter_id[1:])


def audit_counter_sequence_order(counter_rows, *, min_origin_probability=0.2):
    """Keep only options strictly between neighbouring existing counter links.

    Existing links are anchors, not ground truth. This function never changes
    them or assigns an event; a unique option is only a review proposal.
    """
    ordered = sorted(counter_rows, key=lambda row: counter_number(row["counter_id"]))
    ids = [counter_number(row["counter_id"]) for row in ordered]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate counter ID")
    anchors = [(counter_number(row["counter_id"]), shot_number(row["shot_id"]))
               for row in ordered if row["shot_id"] is not None]
    reversals = [{"earlier_counter_id": f"B{left[0]:02d}",
                  "earlier_shot_id": f"S{left[1]}",
                  "later_counter_id": f"B{right[0]:02d}",
                  "later_shot_id": f"S{right[1]}"}
                 for left, right in zip(anchors, anchors[1:])
                 if right[1] <= left[1]]
    proposals = []
    for row in ordered:
        if row["shot_id"] is not None or len(row["candidate_shots"]) < 2:
            continue
        counter = counter_number(row["counter_id"])
        lower = next(((c, s) for c, s in reversed(anchors) if c < counter), None)
        upper = next(((c, s) for c, s in anchors if c > counter), None)
        contradictory_anchors = bool(lower and upper and lower[1] >= upper[1])
        options = []
        seen = set()
        for candidate in row["candidate_shots"]:
            shot_id = candidate["shot_id"]
            shot = shot_number(shot_id)
            if shot in seen:
                raise ValueError(f"Duplicate option for {row['counter_id']}: {shot_id}")
            seen.add(shot)
            in_order = ((lower is None or shot > lower[1]) and
                        (upper is None or shot < upper[1]))
            passes = (not contradictory_anchors and in_order and
                      candidate["origin_probability"] >= min_origin_probability)
            options.append({"shot_id": shot_id,
                            "origin_probability": candidate["origin_probability"],
                            "strictly_between_anchors": in_order,
                            "passes_order_and_origin": passes})
        survivors = [option["shot_id"] for option in options
                     if option["passes_order_and_origin"]]
        proposals.append({"counter_id": row["counter_id"],
                          "counter_colour": row["colour"],
                          "lower_anchor": (None if lower is None else
                                           {"counter_id": f"B{lower[0]:02d}",
                                            "shot_id": f"S{lower[1]}"}),
                          "upper_anchor": (None if upper is None else
                                           {"counter_id": f"B{upper[0]:02d}",
                                            "shot_id": f"S{upper[1]}"}),
                          "contradictory_anchors": contradictory_anchors,
                          "proposed_shot_id": survivors[0] if len(survivors) == 1 else None,
                          "options": options})
    return {"anchor_reversals": reversals,
            "multi_option_counter_proposals": proposals}
