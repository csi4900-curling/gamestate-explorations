from prototype.board_state_comparison import compare_board_observations


def test_matches_rotated_official_diagram_by_colour_and_position():
    official = [{"colour": "red", "house_radius_coordinates": [0.5, 0.25]},
                {"colour": "yellow", "house_radius_coordinates": [-0.25, -0.5]}]
    video = [{"colour": "red", "canonical_lateral_house_radii": -0.51,
              "longitudinal_house_radii": 0.26},
             {"colour": "yellow", "canonical_lateral_house_radii": 0.26,
              "longitudinal_house_radii": -0.49}]
    result = compare_board_observations(video, official, official_house_center_y=160)
    assert result["matched_count"] == 2
    assert result["mean_matched_distance_house_radii"] < 0.02


def test_distant_colour_symbol_is_left_unmatched():
    official = [{"colour": "yellow", "house_radius_coordinates": [0, 0]}]
    video = [{"colour": "yellow", "canonical_lateral_house_radii": 1,
              "longitudinal_house_radii": 1}]
    result = compare_board_observations(video, official, official_house_center_y=440)
    assert result["matched_count"] == 0
    assert len(result["unmatched_video"]) == len(result["unmatched_official"]) == 1
