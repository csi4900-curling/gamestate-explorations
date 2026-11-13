import cv2
import numpy as np

from right_large_cap_proposals import right_large_cap_proposals


def test_larger_stone_cap_can_be_proposed_inside_right_roi():
    frame = np.full((360, 640, 3), 235, dtype=np.uint8)
    cv2.rectangle(frame, (400, 250), (419, 259), (0, 230, 230), -1)
    result = right_large_cap_proposals(frame)
    assert any(row["cap_area_px2"] > 120 for row in result["yellow"])


def test_oversized_blob_and_left_panel_remain_excluded():
    frame = np.full((360, 640, 3), 235, dtype=np.uint8)
    cv2.rectangle(frame, (400, 250), (435, 270), (0, 230, 230), -1)
    cv2.rectangle(frame, (100, 250), (119, 259), (0, 230, 230), -1)
    assert not right_large_cap_proposals(frame)["yellow"]
