import pytest

from display_context_handoff import attach_display_context


def fixture():
    handoff = {"timeline": [
        {"candidate_id": "S01", "passage_time_s": 1.5,
         "end_identity": None, "simulation_ready": False},
        {"candidate_id": "S02", "passage_time_s": 2.5,
         "end_identity": None, "simulation_ready": False},
    ]}
    context = {"events": [
        {"event_id": "S01", "crossing_time_s": 1.5,
         "display_context_status": "bracketed_display_end",
         "displayed_end": 2, "left_marker": None,
         "right_marker": None, "physical_end": None},
        {"event_id": "S02", "crossing_time_s": 2.5,
         "display_context_status": "bracketed_display_change",
         "displayed_end": None, "left_marker": None,
         "right_marker": None, "physical_end": None},
    ]}
    return handoff, context


def test_displayed_end_does_not_become_physical_end():
    handoff, context = fixture()
    rows = attach_display_context(handoff, context)
    assert rows[0]["broadcast_end_display"]["displayed_end"] == 2
    assert rows[0]["end_identity"] is None
    assert rows[1]["broadcast_end_display"]["status"] == "bracketed_display_change"
    assert all(not row["simulation_ready"] for row in rows)


def test_rejects_missing_candidate_or_assigned_physical_end():
    handoff, context = fixture()
    context["events"].pop()
    with pytest.raises(ValueError):
        attach_display_context(handoff, context)
    handoff, context = fixture()
    context["events"][0]["physical_end"] = 2
    with pytest.raises(ValueError):
        attach_display_context(handoff, context)
