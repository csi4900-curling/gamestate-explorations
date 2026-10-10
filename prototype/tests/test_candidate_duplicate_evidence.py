from prototype.candidate_duplicate_evidence import (
    contained_visual_duplicates, fuse_candidate_events,
)


def event(identifier, window, colour, counter=None):
    return {"candidate_id": identifier, "release_window_s": window,
            "colour": colour, "counter_id": counter}


def test_contained_same_colour_evidence_fuses_without_losing_sources():
    events = [event("A", [10, 20], "red", "B1"),
              event("B", [12, 14], "red"),
              event("C", [15, 18], "red"),
              event("D", [21, 25], "yellow")]
    duplicates = contained_visual_duplicates(events)
    assert set(duplicates) == {"B", "C"}
    fused = fuse_candidate_events(events, duplicates)
    assert len(fused) == 2
    assert next(row for row in fused if row["primary_candidate_id"] == "A")["source_candidate_ids"] == ["A", "B", "C"]


def test_colour_conflict_and_adjacent_window_do_not_fuse():
    events = [event("A", [10, 20], "red", "B1"),
              event("B", [12, 14], "yellow"),
              event("C", [20, 25], "red")]
    assert contained_visual_duplicates(events) == {}


def test_two_possible_anchors_force_abstention():
    events = [event("A", [10, 25], "red", "B1"),
              event("B", [12, 24], "red", "B2"),
              event("C", [15, 18], "red")]
    assert contained_visual_duplicates(events) == {}
