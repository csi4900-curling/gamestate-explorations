from prototype.right_passage_timeline_overlay import build_overlay


def event(id, colour, time):
    return {"id": id, "colour": colour, "crossing_time_s": time}


def proposal(id, colour, time, direction="negative_y"):
    return {"raw_track_id": id, "colour_claim": colour,
            "passage": {"time_s": time}, "direction": direction,
            "observed_prefix_interval_s": [time - 1, time + 1],
            "observed_prefix_points": []}


def test_only_unique_short_stone_temporal_link_is_provisional():
    left = [event("L1", "yellow", 10), event("L2", "red", 30)]
    right = [proposal("stone", "yellow", 18),
             proposal("person", "red", 35),
             proposal("long", "red", 36),
             proposal("wrong_direction", "red", 37, "positive_y")]
    classes = {"stone": "moving_stone", "person": "person_or_wheelchair",
               "long": "stone_pixels_identity_uncertain",
               "wrong_direction": "moving_stone"}
    result = build_overlay(left, right, classes)
    assert result["rows"][0]["conditional_left_event_id"] == "L1"
    assert [row["fusion_status"] for row in result["rows"][1:]] == [
        "source_reviewed_person_candidate", "stone_pixels_long_track_identity_review",
        "right_stone_without_directional_left_review"]
    assert result["rows"][3]["conditional_left_event_id"] is None
    assert result["left_events_without_short_right_link"] == ["L2"]


def test_ambiguous_left_and_duplicate_right_paths_abstain():
    left = [event("L1", "yellow", 10), event("L2", "yellow", 12),
            event("L3", "red", 30)]
    right = [proposal("ambiguous", "yellow", 18),
             proposal("R1", "red", 35), proposal("R2", "red", 36)]
    result = build_overlay(left, right, {r["raw_track_id"]: "moving_stone"
                                         for r in right})
    assert result["rows"][0]["fusion_status"] == "multiple_directional_left_events_review"
    assert [row["fusion_status"] for row in result["rows"][1:]] == [
        "multiple_right_stone_paths_review", "multiple_right_stone_paths_review"]
    assert all(row["conditional_left_event_id"] is None for row in result["rows"])


def test_positive_y_short_stone_links_to_later_left_but_long_path_stays_unresolved():
    left = [event("L1", "yellow", 18)]
    right = [proposal("short", "yellow", 10, "positive_y"),
             proposal("long", "yellow", 11, "positive_y")]
    result = build_overlay(left, right, {"short": "moving_stone",
                                         "long": "stone_pixels_identity_uncertain"})
    assert result["rows"][0]["conditional_left_event_id"] == "L1"
    assert result["rows"][1]["conditional_left_event_id"] is None
    assert result["rows"][1]["direction_aware_same_colour_left_ids_within_lag"] == ["L1"]
