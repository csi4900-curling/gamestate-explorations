import pytest

from prototype.split_house_cap_geometry import (
    house_location_tier,
    normalized_house_distance,
)


def ellipse():
    return {"center_px": [490, 160], "axis_lengths_px": [280, 28], "angle_degrees_opencv": 90}


def test_camera_relative_house_distance_separates_front_guard_area():
    assert normalized_house_distance(ellipse(), [490, 160]) == 0
    assert normalized_house_distance(ellipse(), [490, 174]) == 1
    assert house_location_tier(normalized_house_distance(ellipse(), [490, 180])) == (
        "outside_painted_house_review"
    )
    assert house_location_tier(normalized_house_distance(ellipse(), [430, 155])) == (
        "near_painted_house_review"
    )


def test_unsupported_rotation_is_explicit():
    bad = ellipse()
    bad["angle_degrees_opencv"] = 45
    with pytest.raises(ValueError, match="Unsupported rotated"):
        normalized_house_distance(bad, [490, 160])
