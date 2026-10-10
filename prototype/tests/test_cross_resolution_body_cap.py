import pytest

from prototype.cross_resolution_body_cap import (compatible_body_path,
                                                 matched_point_offsets)


def test_synchronous_body_cap_correspondence_keeps_pixel_offsets():
    caps = [{"time_s": 10, "pixel": [470, 230]},
            {"time_s": 11, "pixel": [471, 250]}]
    bodies = [{"time_s": 10, "center_1080p_px": [1410, 714]},
              {"time_s": 11, "center_1080p_px": [1413, 774]}]
    result = compatible_body_path(caps, bodies)
    assert result["common_observation_count"] == 2
    assert result["median_body_minus_cap_x_360p_px"] == 0
    assert result["median_body_minus_cap_y_360p_px"] == 8
    assert compatible_body_path(caps, [{**bodies[0], "center_1080p_px": [1500, 714]},
                                       bodies[1]]) is None


def test_duplicate_highres_time_cannot_create_correspondence():
    caps = [{"time_s": 10, "pixel": [470, 230]}]
    body = {"time_s": 10, "center_1080p_px": [1410, 714]}
    with pytest.raises(ValueError, match="Duplicate"):
        matched_point_offsets(caps, [body, body])
