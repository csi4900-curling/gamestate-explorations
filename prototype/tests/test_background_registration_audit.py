import cv2
import numpy as np

from background_registration_audit import registration_support


def test_excluding_moving_object_removes_object_dominated_fit():
    rng = np.random.default_rng(7)
    first = np.full((360, 640, 3), 225, np.uint8)
    for x, y in rng.integers([300, 150], [370, 220], size=(90, 2)):
        cv2.circle(first, (int(x), int(y)), 2, (0, 0, 200), -1)
    shifted = cv2.warpAffine(first, np.float32([[1, 0, 8], [0, 1, 0]]), (640, 360))
    unmasked = registration_support(first, shifted)
    masked = registration_support(first, shifted,
                                  exclude_bbox=[300, 150, 70, 70], margin_px=30)
    assert unmasked["inliers"] >= 30
    assert masked["tracked_features"] == 0
    assert not masked["reliable_by_existing_rule"]
