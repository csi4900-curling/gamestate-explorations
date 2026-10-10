from prototype.visual_counter_gap_screen import screen_visual_counter_gaps


def counter(key, colour, time, before, after, evidence):
    return {"id": key, "colour": colour, "crossing_time_s": time,
            "remaining_before": before, "remaining_after": after,
            "evidence_interval_s": evidence}


def visual(key, colour, interval):
    return {"candidate_id": key, "counter_id": None, "colour": colour,
            "release_window_s": interval}


def test_stable_state_flags_extra_colour_but_does_not_reject():
    counters = [counter("B1", "red", 10, [2, 2], [1, 2], [9, 10]),
                counter("B2", "yellow", 30, [1, 2], [1, 1], [28, 30])]
    row = screen_visual_counter_gaps([visual("T1", "red", [20, 22])], counters)["rows"][0]
    assert row["status"] == "continuous_state_no_intervening_decrement"
    assert not row["hard_reject"]


def test_overlapping_same_colour_counter_can_be_duplicate():
    counters = [counter("B1", "red", 10, [2, 2], [1, 2], [7, 10])]
    row = screen_visual_counter_gaps([visual("T1", "red", [8, 9])], counters)["rows"][0]
    assert row["status"] == "overlaps_compatible_counter_evidence"


def test_state_gap_can_accommodate_candidate_colour():
    counters = [counter("B1", "red", 10, [3, 3], [2, 3], [9, 10]),
                counter("B2", "red", 30, [2, 2], [1, 2], [28, 30])]
    row = screen_visual_counter_gaps([visual("T1", "yellow", [20, 22])], counters)["rows"][0]
    assert row["status"] == "state_gap_could_contain_colour_decrement"
