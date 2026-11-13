from prototype.official_counter_alignment import align_counter_events


def game():
    return {
        "team_handle_colours": {"A": "red", "B": "yellow"},
        "ends": [
            {
                "end": 1,
                "shots": [
                    {"team": "A" if i % 2 == 0 else "B", "official_shot_id": f"E1-S{i + 1}"}
                    for i in range(16)
                ],
            },
            {
                "end": 2,
                "shots": [
                    {"team": "B" if i % 2 == 0 else "A", "official_shot_id": f"E2-S{i + 1}"}
                    for i in range(13)
                ],
            },
        ],
    }


def event(identifier, after, colour):
    return {
        "id": identifier,
        "remaining_after": after,
        "colour": colour,
        "crossing_time_s": 1,
        "evidence_interval_s": [0, 1],
    }


def test_unique_slots_conflicts_duplicates_and_reset():
    rows = align_counter_events(
        game(),
        [
            event("B1", [7, 8], "red"),
            event("B2", [7, 7], "yellow"),
            event("B3", [7, 7], "yellow"),
            event("B3a", [1, 1], "yellow"),
            event("B4", [8, 7], "red"),
            event("B5", [7, 7], "red"),
            event("B6", [0, 0], "red"),
        ],
    )
    assert [row["status"] for row in rows] == [
        "unique_colour_concordant",
        "duplicate_counter_slot",
        "duplicate_counter_slot",
        "unique_colour_concordant",
        "colour_conflict",
        "unique_colour_concordant",
        "outside_official_shot_range",
    ]
    assert rows[4]["official_shot_id"] == "E2-S1"


def test_one_matching_colour_amid_duplicate_slot_is_retained():
    rows = align_counter_events(
        game(),
        [
            event("B1", [7, 8], "red"),
            event("B2", [7, 7], "yellow"),
            event("B3", [7, 7], "red"),
            event("B4", [1, 1], "yellow"),
            event("B5", [8, 7], "yellow"),
        ],
    )
    assert rows[1]["status"] == "unique_colour_concordant_amid_duplicate"
    assert rows[2]["status"] == "duplicate_slot_colour_conflict"
