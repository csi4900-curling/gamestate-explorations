import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from span_context_confirmation import confirm_span_context


def event(name, time, *, x=160, colour="red", direction="negative_y"):
    return {"id": name, "crossing_time_s": time, "crossing_x_px": x,
            "colour": colour, "view_motion": direction}


def motion(name, changed):
    return {"id": name, "changed_px_80x80": changed}


def test_motion_extent_and_fragment_screen_retains_reasons():
    events = [event("stone", 10), event("fragment", 15, x=166),
              event("person", 50), event("off_ice", 100, x=250)]
    rows = [motion("stone", 400), motion("fragment", 420),
            motion("person", 2000), motion("off_ice", 300)]
    decisions = confirm_span_context(events, rows)
    assert {item["id"]: item["reason"] for item in decisions} == {
        "stone": "compact_tracked_motion",
        "fragment": "fragment_of_recent_passage",
        "person": "large_surrounding_motion",
        "off_ice": "outside_ice_corridor",
    }


def test_other_colour_is_not_collapsed_as_a_fragment():
    events = [event("red", 10), event("yellow", 15, colour="yellow")]
    rows = [motion("red", 300), motion("yellow", 300)]
    assert [item["status"] for item in confirm_span_context(events, rows)] == [
        "confirmed", "confirmed"
    ]
