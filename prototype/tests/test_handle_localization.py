import cv2
import numpy as np

from prototype.handle_localization import locate_yellow_handle


def frame_with_yellow(*rectangles):
    image = np.full((240, 320, 3), 220, np.uint8)
    yellow = cv2.cvtColor(np.uint8([[[30, 230, 230]]]),
                          cv2.COLOR_HSV2BGR)[0, 0]
    for first, last in rectangles:
        cv2.rectangle(image, first, last, tuple(int(v) for v in yellow), -1)
    return image


def test_unique_local_handle_recenters_crop():
    frame = frame_with_yellow(((130, 76), (150, 90)))
    result = locate_yellow_handle(frame, 110, 100)
    assert result["status"] == "unique_local_yellow_component"
    assert result["center_pixel"] == [140, 100]


def test_multiple_nearby_yellow_components_abstain():
    frame = frame_with_yellow(((105, 76), (120, 90)),
                              ((145, 76), (160, 90)))
    result = locate_yellow_handle(frame, 110, 100)
    assert result["status"] == "ambiguous_multiple_yellow_components"
    assert result["center_pixel"] is None


def test_frame_edge_abstains():
    result = locate_yellow_handle(frame_with_yellow(), 10, 10)
    assert result["status"] == "crop_out_of_frame"
