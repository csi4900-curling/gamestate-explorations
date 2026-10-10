import cv2
import numpy as np
import pytest

from prototype.split_panel_camera_registration import (
    camera_relative_pair, edge_alignment_support, estimate_transform,
    panel_for_pixel, panel_pixel, resize_panel)


def test_panel_coordinates_preserve_split_screen_aspect_ratio():
    source = np.zeros((1080, 1920, 3), np.uint8)
    source[:, :960] = (255, 0, 0)
    source[:, 960:] = (0, 0, 255)
    assert resize_panel(source, 0).shape[:2] == (720, 640)
    assert tuple(resize_panel(source, 1)[360, 320]) == (0, 0, 255)
    assert panel_for_pixel((1370, 900)) == 1
    assert panel_pixel((1370, 900), 1) == pytest.approx((273.3333, 600),
                                                          abs=0.001)
    with pytest.raises(ValueError):
        panel_pixel((1370, 900), 0)


def test_camera_motion_is_removed_but_independent_target_motion_remains():
    rng = np.random.default_rng(2)
    before = np.full((720, 640, 3), 235, np.uint8)
    for x, y in rng.integers([20, 160], [620, 700], size=(500, 2)):
        cv2.circle(before, (int(x), int(y)), 2, (160, 160, 160), -1)
    after = cv2.warpAffine(before, np.float32([[1, 0, 4], [0, 1, 3]]),
                           (640, 720), borderValue=(235, 235, 235))
    fit = estimate_transform(before, after, (300, 500))
    assert fit["status"] == "registered"
    assert fit["inliers"] >= 30
    assert fit["matrix"][:, 2] == pytest.approx([4, 3], abs=0.5)

    frames = {0.0: before, 0.25: after}
    static = camera_relative_pair((300, 500), (304, 503), 0, 0.25,
                                  frames.__getitem__)
    moving = camera_relative_pair((300, 500), (324, 503), 0, 0.25,
                                  frames.__getitem__)
    assert static["camera_residual_px"] < 1
    assert moving["camera_residual_px"] == pytest.approx(20, abs=1)


def test_scene_edges_reject_a_foreground_translation_when_rink_is_static():
    image = np.full((720, 640), 235, np.uint8)
    for x in range(20, 640, 40):
        cv2.line(image, (x, 160), (x, 690), 130, 2)
    for y in range(180, 720, 40):
        cv2.line(image, (0, y), (639, y), 130, 2)
    mask = np.full((720, 640), 255, np.uint8)
    false_foreground_fit = np.float32([[1, 0, 8], [0, 1, 9]])
    edge = edge_alignment_support(image, image, mask, false_foreground_fit)
    assert edge["edge_identity_support"] > edge["edge_transform_support"] + 0.05
