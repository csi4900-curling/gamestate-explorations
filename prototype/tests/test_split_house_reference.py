import cv2
import numpy as np

from prototype.split_house_reference import fit_right_house_paint


def test_split_right_house_paint_fits_two_visible_halves():
    frame = np.full((360, 640, 3), 235, dtype=np.uint8)
    blue = cv2.cvtColor(np.uint8([[[100, 120, 180]]]), cv2.COLOR_HSV2BGR)[0, 0]
    cv2.ellipse(frame, (480, 160), (135, 14), 0, 0, 360,
                tuple(int(v) for v in blue), -1)
    frame[135:185, 470:490] = 235
    result = fit_right_house_paint(frame)
    assert result is not None
    assert result["paint_component_count"] == 2
    assert abs(result["center_px"][0] - 480) < 5
    assert abs(result["center_px"][1] - 160) < 5
    assert 250 < result["axis_lengths_px"][0] < 300


def test_house_reference_abstains_without_paint():
    frame = np.full((360, 640, 3), 235, dtype=np.uint8)
    assert fit_right_house_paint(frame) is None
