import pytest

from event_review_segments import build_review_segments


def event(identifier, source_shots, kind="visual_origin_existing", held=None):
    return {"event_id": identifier, "candidate_class": kind,
            "counter_id": identifier, "colour": "yellow",
            "colour_status": "resolved", "source_shot_ids": source_shots,
            "attached_held_evidence": held,
            "delivery_window_s": [0.0, 10.0],
            "observed_travel_window_s": [10.0, 20.0] if kind.startswith("counter") else None}


def shots():
    return [{"id": f"S{i}", "interval_s": [10.0 * (i - 1), 10.0 * i]}
            for i in range(1, 5)]


def test_travel_review_includes_only_unoccupied_previous_shot():
    travel = event("B1", ["S3"], "counter_linked_travel_only_provisional")
    rows = build_review_segments([travel], shots(), [{"time_s": 22.0}])
    assert rows[0]["review_shot_ids"] == ["S2", "S3"]
    assert rows[0]["evidence_core_s"] == [10.0, 30.0]
    assert rows[0]["review_window_s"] == [8.0, 35.0]
    assert rows[0]["possible_internal_edit_times_s"] == [22.0]
    assert rows[0]["physical_release_time_s"] is None
    prior = event("B0", ["S2"])
    rows = build_review_segments([prior, travel], shots(), [])
    travel_row = next(row for row in rows if row["event_id"] == "B1")
    assert travel_row["review_shot_ids"] == ["S3"]
    assert travel_row["unoccupied_previous_shot_added"] is None


def test_rejects_evidence_shot_used_by_two_candidates():
    with pytest.raises(ValueError, match="assigned to multiple events"):
        build_review_segments([event("B1", ["S2"]), event("B2", ["S2"])],
                              shots(), [])
