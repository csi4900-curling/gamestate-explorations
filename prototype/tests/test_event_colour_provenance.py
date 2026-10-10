import pytest

from event_colour_provenance import annotate_event_colours


def decision(shot_id, colours):
    return {"shot_id": shot_id, "status": "corroborated_candidate",
            "supported_colours": colours,
            "colour": colours[0] if len(colours) == 1 else None,
            "colour_status": "unique" if len(colours) == 1 else "ambiguous"}


def event(shot_id, colour, counter_id=None, *, conflict=False):
    return {"shot_id": shot_id, "colour": colour, "counter_id": counter_id,
            "evidence_sources": ["visual_origin_and_adjacent_motion"],
            "colour_status": "conflict" if conflict else "resolved" if colour else "ambiguous"}


def counter(counter_id, shot_id, colour):
    return {"counter_id": counter_id, "shot_id": shot_id, "colour": colour}


def test_ambiguous_visual_colour_is_explicitly_counter_derived():
    events = [event("S1", "yellow", "B1")]
    annotated = annotate_event_colours(
        events, [decision("S1", ["red", "yellow"])],
        [counter("B1", "S1", "yellow")])
    assert annotated[0]["colour_provenance"] == {
        "basis": "counter_with_ambiguous_visual",
        "visual_supported_colours": ["red", "yellow"],
        "visual_unique_colour": None,
        "counter_id": "B1", "counter_colour": "yellow",
        "resolved_colour": "yellow", "counter_is_delayed_proxy": True,
    }
    assert "colour_provenance" not in events[0]


def test_visual_and_counter_routes_and_conflict_are_distinct():
    events = [event("S1", "red"), event("S2", "yellow", "B2"),
              event("S3", None, "B3", conflict=True)]
    decisions = [decision("S1", ["red"]), decision("S2", ["yellow"]),
                 decision("S3", ["red"])]
    counters = [counter("B2", "S2", "yellow"), counter("B3", "S3", "yellow")]
    annotated = annotate_event_colours(events, decisions, counters)
    assert [row["colour_provenance"]["basis"] for row in annotated] == [
        "visual_only", "visual_and_counter_agree", "visual_counter_conflict"]


def test_counter_without_visual_and_unresolved_visual():
    events = [event("S1", "red", "B1"), event("S2", None)]
    decisions = [{"shot_id": "S1", "status": "unconfirmed",
                  "supported_colours": [], "colour": None,
                  "colour_status": "unsupported"},
                 decision("S2", ["red", "yellow"])]
    annotated = annotate_event_colours(events, decisions,
                                       [counter("B1", "S1", "red")])
    assert [row["colour_provenance"]["basis"] for row in annotated] == [
        "counter_without_corroborated_visual", "unresolved_ambiguous_visual"]


def test_contradictory_fused_colour_fails_closed():
    with pytest.raises(ValueError, match="contradicts evidence"):
        annotate_event_colours([event("S1", "red", "B1")],
                               [decision("S1", ["red", "yellow"])],
                               [counter("B1", "S1", "yellow")])


def test_counter_from_a_different_shot_fails_closed():
    with pytest.raises(ValueError, match="Counter association mismatch"):
        annotate_event_colours([event("S1", "red", "B1")],
                               [decision("S1", ["red", "yellow"])],
                               [counter("B1", "S2", "red")])
