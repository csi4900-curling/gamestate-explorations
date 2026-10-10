from prototype.counter_gap_inventory import inventory_gaps


def test_single_same_end_candidate_is_only_a_proposal():
    slots = [
        {
            "end": 1,
            "shot_number": 1,
            "official_shot_id": "E1S1",
            "official_colour": "red",
            "counter_id": "B1",
            "video_candidate_shot_id": "S1",
            "provisional_delivery_window_s": [10, 12],
        },
        {
            "end": 1,
            "shot_number": 2,
            "official_shot_id": "E1S2",
            "official_colour": "yellow",
            "counter_id": None,
            "video_candidate_shot_id": None,
        },
        {
            "end": 1,
            "shot_number": 3,
            "official_shot_id": "E1S3",
            "official_colour": "red",
            "counter_id": "B2",
            "video_candidate_shot_id": "S3",
            "provisional_delivery_window_s": [30, 32],
        },
    ]
    events = [
        {"shot_id": "S1", "counter_id": "B1"},
        {"shot_id": "S2", "counter_id": None, "colour": "yellow", "delivery_window_s": [20, 22]},
        {"shot_id": "S3", "counter_id": "B2"},
    ]
    display = [{"shot_id": "S2", "displayed_end": 1}]
    gaps = inventory_gaps(slots, events, display)
    assert gaps[0]["unique_order_colour_display_proposal"] == {
        "official_shot_id": "E1S2",
        "video_candidate_shot_id": "S2",
    }
    display[0]["displayed_end"] = None
    assert inventory_gaps(slots, events, display)[0]["unique_order_colour_display_proposal"] is None
    events[1]["colour"] = "red"
    assert (
        inventory_gaps(slots, events, display)[0]["counterless_candidates"][0][
            "compatible_missing_slot_ids"
        ]
        == []
    )
