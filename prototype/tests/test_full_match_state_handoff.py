from prototype.full_match_state_handoff import build_state_rows


def test_reference_and_video_state_keep_separate_provenance():
    slots = [
        {
            "official_shot_id": "E1S1",
            "end": 1,
            "shot_number": 1,
            "official_colour": "red",
            "counter_id": "B1",
            "counter_crossing_time_s": 20,
            "video_candidate_shot_id": "S1",
            "provisional_delivery_window_s": [10, 18],
        },
        {
            "official_shot_id": "E1S2",
            "end": 1,
            "shot_number": 2,
            "official_colour": "yellow",
            "counter_id": None,
            "counter_crossing_time_s": None,
            "video_candidate_shot_id": None,
            "provisional_delivery_window_s": None,
        },
    ]
    shots = [
        {
            "official_shot_id": shot_id,
            "team": team,
            "shooter": "P",
            "shot_type": "Draw",
            "rotation": "clockwise",
        }
        for shot_id, team in [("E1S1", "CAN"), ("E1S2", "NOR")]
    ]
    boards = [
        {
            "official_shot_id": "E1S1",
            "stones": [{"colour": "red", "house_radius_coordinates": [0.2, 0.3]}],
        },
        {"official_shot_id": "E1S2", "stones": []},
    ]
    candidates = [
        {
            "shot_id": "S1",
            "counter_id": "B1",
            "camera_shot_boards": [
                {
                    "camera_shot_id": "S2",
                    "observation_interval_s": [22, 28],
                    "stable_image_relative_stones": [
                        {"colour": "red", "image_house_radius_coordinates": [0.2, 0.3]}
                    ],
                    "detected_delivery_side": None,
                }
            ],
        },
        {
            "shot_id": "S3",
            "counter_id": None,
            "delivery_window_s": [30, 40],
            "camera_shot_boards": [],
        },
    ]
    rows = build_state_rows(
        slots,
        shots,
        boards,
        candidates,
        [{"official_shot_id": "E1S2", "video_candidate_shot_id": "S3"}],
        [],
        [],
    )
    assert rows[0]["official_reference"]["post_shot_diagram_stones"]
    assert rows[0]["video_post_shot_state"]["camera_groups"]
    assert (
        rows[1]["video_event_evidence"]["association_basis"]
        == "unique_gap_order_colour_display_proposal"
    )
    assert rows[1]["video_post_shot_state"]["status"] == "unobserved"
    assert all(not row["video_physics_simulation_ready"] for row in rows)
