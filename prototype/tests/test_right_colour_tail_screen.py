import cv2
import numpy as np
import pytest

from prototype.right_colour_tail_screen import predict_next_cap_center, screen_next_colour_frame


def test_cap_prediction_scales_into_aligned_high_resolution_frame():
    points = [{"time_s": 10, "pixel": [400, 200]}, {"time_s": 11, "pixel": [410, 220]}]
    assert predict_next_cap_center(points) == [1260, 720]
    with pytest.raises(ValueError, match="consecutively"):
        predict_next_cap_center([points[0], {"time_s": 14, "pixel": [410, 220]}])


def test_unique_colour_component_and_ambiguous_abstention():
    frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
    cv2.rectangle(frame, (1280, 680), (1300, 700), (0, 255, 255), -1)
    one = screen_next_colour_frame(frame, "yellow", [1300, 690])
    assert one["status"] == "unique_colour_component_provisional"
    assert len(one["candidates"]) == 1
    cv2.rectangle(frame, (1307, 680), (1327, 700), (0, 255, 255), -1)
    two = screen_next_colour_frame(frame, "yellow", [1300, 690])
    assert two["status"] == "abstain_ambiguous_or_absent"
    assert len(two["candidates"]) == 2
