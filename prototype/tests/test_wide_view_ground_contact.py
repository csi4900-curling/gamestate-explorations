import cv2
import numpy as np

from prototype.wide_view_ground_contact import contact_below_cap


def test_contact_uses_neutral_body_bottom_over_saturated_rink():
    frame = np.full((80, 80, 3), (210, 100, 15), dtype=np.uint8)
    cv2.rectangle(frame, (30, 34), (50, 47), (120, 125, 130), -1)
    cv2.rectangle(frame, (35, 30), (45, 35), (20, 30, 180), -1)

    point = contact_below_cap(frame, (40, 30))

    assert point is not None
    assert point["pixel"] == [40.0, 48]


def test_contact_abstains_without_visible_neutral_body():
    frame = np.full((80, 80, 3), (210, 100, 15), dtype=np.uint8)
    cv2.rectangle(frame, (35, 30), (45, 35), (20, 30, 180), -1)

    assert contact_below_cap(frame, (40, 30)) is None
