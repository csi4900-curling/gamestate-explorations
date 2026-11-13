import cv2
import numpy as np
import pytest

from local_colour_cap_probe import local_cap_components


def test_keeps_separate_colour_components_and_absolute_centers():
    frame = np.zeros((100, 120, 3), dtype=np.uint8)
    cv2.circle(frame, (35, 45), 9, (0, 0, 255), -1)
    cv2.circle(frame, (70, 40), 8, (0, 255, 255), -1)
    cv2.circle(frame, (82, 72), 7, (0, 255, 255), -1)
    assert len(local_cap_components(frame, (20, 20, 100, 90), "red")) == 1
    yellow = local_cap_components(frame, (20, 20, 100, 90), "yellow")
    assert len(yellow) == 2
    assert {tuple(row["centroid_px_1080"]) for row in yellow} == {(70.0, 40.0), (82.0, 72.0)}


@pytest.mark.parametrize("roi,colour", [((0, 0, 121, 20), "red"), ((0, 0, 20, 20), "blue")])
def test_rejects_invalid_input(roi, colour):
    with pytest.raises(ValueError):
        local_cap_components(np.zeros((100, 120, 3), dtype=np.uint8), roi, colour)
