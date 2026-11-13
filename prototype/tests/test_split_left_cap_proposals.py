import cv2
import numpy as np

from prototype.split_left_cap_proposals import left_colour_cap_proposals


def test_detects_left_colour_blob_and_excludes_right_panel():
    frame = np.full((360, 640, 3), 180, np.uint8)
    cv2.rectangle(frame, (95, 190), (103, 197), (0, 240, 255), -1)
    cv2.rectangle(frame, (415, 190), (423, 197), (0, 240, 255), -1)
    found = left_colour_cap_proposals(frame)
    assert len(found) == 1
    assert found[0]["colour"] == "yellow"
    assert found[0]["pixel"] == [99.5, 194.0]
