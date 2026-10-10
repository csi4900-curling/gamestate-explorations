"""Conservatively reconcile official shot order with broadcast counter reads."""

from collections import Counter


def align_counter_events(official_game, counter_events):
    """Return one row per counter event; only unique, colour-consistent slots align.

    A large rise in remaining stones marks a new end. The broadcast counter
    may blink or skip, so duplicate slots and colour conflicts are retained.
    """
    groups = [[]]
    for event in counter_events:
        if groups[-1]:
            previous = groups[-1][-1]
            rise = sum(event["remaining_after"]) - sum(previous["remaining_after"])
            if rise >= 5:
                groups.append([])
        groups[-1].append(event)
    if len(groups) != len(official_game["ends"]):
        raise ValueError("Counter reset segmentation does not match official end count")

    rows = []
    for end, events in zip(official_game["ends"], groups):
        numbers = [16 - sum(event["remaining_after"]) for event in events]
        frequency = Counter(numbers)
        matching_by_number = Counter(
            number for event, number in zip(events, numbers)
            if 1 <= number <= len(end["shots"])
            and event["colour"] == official_game["team_handle_colours"][end["shots"][number - 1]["team"]])
        for event, number in zip(events, numbers):
            official_shot = end["shots"][number - 1] if 1 <= number <= len(end["shots"]) else None
            expected_colour = (official_game["team_handle_colours"][official_shot["team"]]
                               if official_shot else None)
            if official_shot is None:
                status = "outside_official_shot_range"
            elif frequency[number] > 1 and matching_by_number[number] == 1:
                status = ("unique_colour_concordant_amid_duplicate"
                          if event["colour"] == expected_colour else "duplicate_slot_colour_conflict")
            elif frequency[number] > 1:
                status = "duplicate_counter_slot"
            elif event["colour"] != expected_colour:
                status = "colour_conflict"
            else:
                status = "unique_colour_concordant"
            rows.append({
                "counter_id": event["id"],
                "counter_time_s": event["crossing_time_s"],
                "counter_evidence_interval_s": event["evidence_interval_s"],
                "remaining_after": event["remaining_after"],
                "counter_colour": event["colour"],
                "official_end": end["end"],
                "inferred_shot_number": number,
                "official_shot_id": official_shot["official_shot_id"] if official_shot else None,
                "official_team": official_shot["team"] if official_shot else None,
                "official_colour": expected_colour,
                "status": status,
            })
    return rows
