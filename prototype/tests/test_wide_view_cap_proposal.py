import cv2
import numpy as np

from prototype.stone_motion_fallback import stone_cap_candidates
from prototype.wide_view_cap_proposal import wide_view_cap_candidates


def test_blue_ring_support_recovers_cap_rejected_by_white_ice_rule():
    frame = np.full((360, 640, 3), (190, 95, 20), dtype=np.uint8)
    cv2.rectangle(frame, (183, 285), (199, 294), (0, 225, 240), -1)
    ellipse = {"center_px": [320, 280], "axis_lengths_px": [86, 282]}

    assert (
        stone_cap_candidates(frame, "yellow", allow_bright_body=True, allow_large_caps=True) == []
    )
    proposed = wide_view_cap_candidates(frame, "yellow", ellipse)

    assert len(proposed) == 1
    assert proposed[0]["pixel"] == [191.5, 290.0]


def test_blue_ring_proposal_rejects_coloured_region_far_from_house():
    frame = np.full((360, 640, 3), (190, 95, 20), dtype=np.uint8)
    cv2.rectangle(frame, (183, 85), (199, 94), (0, 225, 240), -1)
    ellipse = {"center_px": [320, 280], "axis_lengths_px": [86, 282]}

    assert wide_view_cap_candidates(frame, "yellow", ellipse) == []
