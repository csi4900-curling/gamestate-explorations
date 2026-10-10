"""Align delayed remaining-stone decrements to independent shot-order slots."""


def align_counter_slots(counter_events, official_ends, team_colours):
    """Map counter states to shot numbers; missing ticks remain empty slots."""
    if not official_ends:
        raise ValueError("No official ends")
    if len({row["id"] for row in counter_events}) != len(counter_events):
        raise ValueError("Duplicate counter event ID")
    end_number = 1
    previous_after = None
    previous_time = None
    assignments = {}
    for event in counter_events:
        before, after = event["remaining_before"], event["remaining_after"]
        time = event["crossing_time_s"]
        if previous_time is not None and time <= previous_time:
            raise ValueError("Counter times are not strictly increasing")
        if any(value < 0 for value in before + after):
            raise ValueError("Negative remaining-stone count")
        if sum(before) - sum(after) != 1:
            raise ValueError(f"Counter event is not one decrement: {event['id']}")
        if previous_after is not None and sum(before) > sum(previous_after):
            end_number += 1
        if end_number > len(official_ends):
            raise ValueError("More counter reset groups than official ends")
        official_end = official_ends[end_number - 1]
        if official_end["end"] != end_number:
            raise ValueError("Official ends are not ordered")
        shot_count = official_end["shot_count"]
        shot_number = shot_count + 1 - sum(before)
        if not 1 <= shot_number <= shot_count:
            raise ValueError(f"Counter outside official shot capacity: {event['id']}")
        key = (end_number, shot_number)
        if key in assignments:
            raise ValueError(f"Multiple counter events for one shot slot: {key}")
        official_shot = official_end["shots"][shot_number - 1]
        expected_colour = team_colours[official_shot["team"]]
        if event["colour"] != expected_colour:
            raise ValueError(f"Counter/official colour conflict: {event['id']}")
        assignments[key] = event
        previous_after = after
        previous_time = time
    if end_number != len(official_ends):
        raise ValueError("Not all official ends reached by counter reset groups")
    slots = []
    summaries = []
    for official_end in official_ends:
        end = official_end["end"]
        rows = []
        for shot in official_end["shots"]:
            number = shot["shot_number"]
            counter = assignments.get((end, number))
            rows.append(
                {
                    "end": end,
                    "shot_number": number,
                    "official_shot_id": shot["official_shot_id"],
                    "official_team": shot["team"],
                    "official_colour": team_colours[shot["team"]],
                    "counter_id": counter["id"] if counter else None,
                    "counter_crossing_time_s": counter["crossing_time_s"] if counter else None,
                    "counter_status": "observed_decrement" if counter else "missing_decrement",
                    "physical_video_throw_verified": False,
                }
            )
        slots.extend(rows)
        summaries.append(
            {
                "end": end,
                "official_shot_count": len(rows),
                "observed_counter_count": sum(row["counter_id"] is not None for row in rows),
                "missing_counter_shot_numbers": [
                    row["shot_number"] for row in rows if row["counter_id"] is None
                ],
            }
        )
    return {
        "official_slot_count": len(slots),
        "aligned_counter_count": len(assignments),
        "missing_counter_slot_count": len(slots) - len(assignments),
        "end_summaries": summaries,
        "slots": slots,
    }
