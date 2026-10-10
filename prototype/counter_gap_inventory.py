"""Inventory counterless candidates between counter-linked video windows.

The inventory uses temporal order and explicit broadcast-display evidence. It
does not decide physical event identity or fill official shot slots.
"""


def inventory_gaps(slots, events, display_rows):
    key = lambda row: (row["end"], row["shot_number"])
    by_display = {row["shot_id"]: row for row in display_rows}
    if len(by_display) != len(display_rows):
        raise ValueError("Duplicate displayed-end shot IDs")
    by_event = {row["shot_id"]: row for row in events}
    if len(by_event) != len(events):
        raise ValueError("Duplicate event shot IDs")
    anchors = [row for row in slots if row["counter_id"] and row["video_candidate_shot_id"]]
    if any(key(a) >= key(b) for a, b in zip(anchors, anchors[1:])):
        raise ValueError("Counter anchors are not in official order")
    if any(
        a["provisional_delivery_window_s"][0] >= b["provisional_delivery_window_s"][0]
        for a, b in zip(anchors, anchors[1:])
    ):
        raise ValueError("Counter anchor video times disagree with official order")
    free = [row for row in events if row["counter_id"] is None]
    output = []
    for left, right in zip(anchors, anchors[1:]):
        start = left["provisional_delivery_window_s"][0]
        end = right["provisional_delivery_window_s"][0]
        missing = [
            row for row in slots if key(left) < key(row) < key(right) and row["counter_id"] is None
        ]
        proposals = [row for row in free if start < row["delivery_window_s"][0] < end]
        if not missing and not proposals:
            continue
        candidate_rows = []
        for event in proposals:
            displayed_end = by_display[event["shot_id"]]["displayed_end"]
            compatible = [
                row["official_shot_id"]
                for row in missing
                if (event["colour"] is None or event["colour"] == row["official_colour"])
                and (displayed_end is None or displayed_end == row["end"])
            ]
            candidate_rows.append(
                {
                    "shot_id": event["shot_id"],
                    "delivery_window_s": event["delivery_window_s"],
                    "candidate_colour": event["colour"],
                    "displayed_end": displayed_end,
                    "compatible_missing_slot_ids": compatible,
                }
            )
        possible_unique = (
            len(missing) == len(candidate_rows) == 1
            and left["end"] == right["end"] == missing[0]["end"]
            and candidate_rows[0]["displayed_end"] == missing[0]["end"]
            and candidate_rows[0]["candidate_colour"] == missing[0]["official_colour"]
        )
        output.append(
            {
                "left_anchor": {
                    "official_shot_id": left["official_shot_id"],
                    "video_candidate_shot_id": left["video_candidate_shot_id"],
                },
                "right_anchor": {
                    "official_shot_id": right["official_shot_id"],
                    "video_candidate_shot_id": right["video_candidate_shot_id"],
                },
                "missing_slots": [
                    {
                        "official_shot_id": row["official_shot_id"],
                        "end": row["end"],
                        "shot_number": row["shot_number"],
                        "official_colour": row["official_colour"],
                    }
                    for row in missing
                ],
                "counterless_candidates": candidate_rows,
                "unique_order_colour_display_proposal": (
                    {
                        "official_shot_id": missing[0]["official_shot_id"],
                        "video_candidate_shot_id": candidate_rows[0]["shot_id"],
                    }
                    if possible_unique
                    else None
                ),
            }
        )
    return output
