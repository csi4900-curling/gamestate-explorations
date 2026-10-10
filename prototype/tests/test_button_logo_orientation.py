import cv2
import numpy as np

from prototype.button_logo_orientation import (logo_colour_signature,
                                               relative_view_rotation)


def emblem(red_point, blue_point):
    frame = np.full((360, 640, 3), 245, dtype=np.uint8)
    cv2.circle(frame, red_point, 4, (20, 20, 220), -1)
    cv2.circle(frame, blue_point, 4, (220, 90, 20), -1)
    return frame


def test_button_colour_order_resolves_half_turn_without_stones():
    first = logo_colour_signature(emblem((310, 175), (320, 185)),
                                  (320, 180), (160, 160))
    rotated = logo_colour_signature(emblem((330, 185), (320, 175)),
                                    (320, 180), (160, 160))

    assert relative_view_rotation(first, rotated) == 180
    assert relative_view_rotation(first, first) == 0


def test_button_cue_abstains_when_occluded_or_axes_conflict():
    first = logo_colour_signature(emblem((310, 175), (320, 185)),
                                  (320, 180), (160, 160))
    missing_blue = np.full((360, 640, 3), 245, dtype=np.uint8)
    cv2.circle(missing_blue, (310, 175), 4, (20, 20, 220), -1)
    mirrored = logo_colour_signature(emblem((330, 175), (320, 185)),
                                     (320, 180), (160, 160))

    assert logo_colour_signature(missing_blue, (320, 180), (160, 160)) is None
    assert relative_view_rotation(first, mirrored) is None
