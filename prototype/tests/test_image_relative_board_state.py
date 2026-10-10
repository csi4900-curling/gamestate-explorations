from prototype.image_relative_board_state import stable_image_boards_by_camera_shot


def test_camera_cut_keeps_opposite_image_positions_separate():
    shots = [{"id": "A", "interval_s": [0, 10]}, {"id": "B", "interval_s": [10, 20]}]
    rows = []
    for t, x in [(1, 60), (3, 60), (5, 60), (11, 40), (13, 40), (15, 40)]:
        rows.append(
            {
                "time_s": t,
                "house": {
                    "center_px": [50, 50],
                    "outer_radius_px": 20,
                    "delivery_side": "uncertain",
                },
                "stones": [{"colour": "red", "pixel": [x, 50]}],
            }
        )
    result = stable_image_boards_by_camera_shot(rows, shots)
    assert [row["camera_shot_id"] for row in result] == ["A", "B"]
    assert [
        row["stable_image_relative_stones"][0]["image_house_radius_coordinates"] for row in result
    ] == [[0.5, 0.0], [-0.5, 0.0]]
    assert all(row["detected_delivery_side"] is None for row in result)
