from prototype.counter_proxy_event_score import score_visual_against_counters


def visual(identifier, start, end, colour):
    return {"shot_id": identifier, "interval_s": [start, end], "colour": colour}


def counter(identifier, time, colour):
    return {"official_shot_id": identifier, "counter_time_s": time, "counter_colour": colour}


def test_monotone_one_to_one_score_preserves_extra_and_miss():
    result = score_visual_against_counters(
        [visual("A", 10, 20, "red"), visual("X", 21, 25, "red"), visual("B", 60, 70, None)],
        [counter("S1", 35, "red"), counter("S2", 85, "yellow"), counter("S3", 140, "red")],
    )
    assert result["matched_count"] == 2
    assert result["unmatched_visual_ids"] == ["X"]
    assert result["unmatched_official_shot_ids"] == ["S3"]
    assert result["unknown_colour_match_count"] == 1


def test_rejects_implausibly_late_counter():
    result = score_visual_against_counters(
        [visual("A", 10, 20, "red")], [counter("S1", 100, "red")]
    )
    assert result["matched_count"] == 0
