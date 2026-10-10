import pytest

from prototype.counter_slot_alignment import align_counter_slots


def official(end):
    return {"end": end, "shot_count": 4,
            "shots": [{"shot_number": i, "team": "A" if i % 2 else "B",
                       "official_shot_id": f"E{end}-S{i}"} for i in range(1, 5)]}


def tick(name, time, before, after, colour):
    return {"id": name, "crossing_time_s": time,
            "remaining_before": before, "remaining_after": after, "colour": colour}


def test_reset_and_skipped_counter_slots_preserve_official_order():
    events = [tick("B1", 10, [2, 2], [1, 2], "red"),
              tick("B2", 20, [1, 2], [1, 1], "yellow"),
              tick("B3", 30, [1, 1], [0, 1], "red"),
              tick("B4", 50, [2, 1], [1, 1], "yellow")]
    result = align_counter_slots(events, [official(1), official(2)],
                                 {"A": "red", "B": "yellow"})
    assert result["official_slot_count"] == 8
    assert result["aligned_counter_count"] == 4
    assert result["end_summaries"][0]["missing_counter_shot_numbers"] == [4]
    assert result["end_summaries"][1]["missing_counter_shot_numbers"] == [1, 3, 4]
    assert result["slots"][5]["counter_id"] == "B4"


def test_colour_conflict_is_not_silently_aligned():
    events = [tick("B1", 10, [2, 2], [1, 2], "yellow")]
    with pytest.raises(ValueError, match="colour conflict"):
        align_counter_slots(events, [official(1)], {"A": "red", "B": "yellow"})


def test_non_decrement_is_rejected():
    events = [tick("B1", 10, [2, 2], [2, 2], "red")]
    with pytest.raises(ValueError, match="not one decrement"):
        align_counter_slots(events, [official(1)], {"A": "red", "B": "yellow"})
