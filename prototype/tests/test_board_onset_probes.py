from prototype.board_onset_probes import onset_frame_detection


def test_maps_local_observation_to_nearest_same_colour_frame_proposal():
    local = {"colour": "red", "view_local_ground_position_m": [1.0, 2.0]}
    frame = [
        {"colour": "yellow", "view_local_ground_position_m": [1.0, 2.0], "pixel_center": [10, 10]},
        {"colour": "red", "view_local_ground_position_m": [5.0, 5.0], "pixel_center": [100, 100]},
        {"colour": "red", "view_local_ground_position_m": [1.1, 2.0], "pixel_center": [30, 40]},
    ]
    match = onset_frame_detection(local, frame)
    assert match["pixel_center_px_1080"] == [30, 40]
    assert match["conditional_ground_distance_m"] == 0.1
    assert match["same_colour_frame_detection_count"] == 2


def test_returns_missing_when_no_same_colour_frame_proposal():
    assert (
        onset_frame_detection(
            {"colour": "red", "view_local_ground_position_m": [0, 0]},
            [{"colour": "yellow", "view_local_ground_position_m": [0, 0], "pixel_center": [5, 5]}],
        )
        is None
    )
