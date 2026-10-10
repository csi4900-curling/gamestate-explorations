import pytest

from prototype.event_sequence_consistency import audit_end_sequence, audit_sequence


def event(identifier, time_s, colour, run="R1"):
    return {"id": identifier, "crossing_time_s": time_s,
            "colour": colour, "source_run_id": run}


def test_flags_nearby_same_colour_but_not_pairs_across_unknown_gap():
    rows = audit_sequence([
        event("A", 10, "red"), event("B", 30, "red"),
        event("C", 60, "yellow"), event("D", 110, "yellow", "R2"),
    ], [[80, 100]])
    assert len(rows) == 2
    assert rows[0]["nearby_review_priority"]
    assert not rows[1]["nearby_review_priority"]
    assert rows[1]["crossed_coverage_gaps_s"] == [[80, 100]]


def test_rejects_duplicate_id_and_timestamp():
    with pytest.raises(ValueError, match="Duplicate event ID"):
        audit_sequence([event("A", 10, "red"), event("A", 20, "yellow")], [])
    with pytest.raises(ValueError, match="timestamp"):
        audit_sequence([event("A", 10, "red"), event("B", 10, "red")], [])


def test_end_boundaries_separate_same_colour_pairs_without_deleting_events():
    events = [event("A", 10, "red"), event("B", 20, "yellow"),
              event("C", 50, "yellow"), event("D", 60, "red"),
              event("E", 65, "red")]
    ends = audit_end_sequence(events, [35])
    assert [row["candidate_count"] for row in ends] == [2, 3]
    assert ends[0]["same_colour_pairs"] == []
    assert ends[1]["same_colour_pairs"] == [
        {"previous_event_id": "D", "current_event_id": "E"}]
    assert ends[1]["candidate_colour_counts"] == {"red": 2, "yellow": 1}


def test_end_audit_reports_capacity_excess_but_allows_short_final_end():
    first = [event(str(i), i + 1, "red" if i % 2 == 0 else "yellow")
             for i in range(16)]
    first.append(event("extra", 17, "red"))
    second = [event(f"last{i}", 30 + i, "red" if i % 2 == 0 else "yellow")
              for i in range(15)]
    ends = audit_end_sequence(first + second, [25])
    assert ends[0]["colour_capacity_excess"] == {"red": 1, "yellow": 0}
    assert ends[1]["candidate_count"] == 15
    assert ends[1]["colour_capacity_excess"] == {"red": 0, "yellow": 0}


def test_end_audit_rejects_ambiguous_boundary():
    with pytest.raises(ValueError, match="boundary"):
        audit_end_sequence([event("A", 10, "red")], [10])
