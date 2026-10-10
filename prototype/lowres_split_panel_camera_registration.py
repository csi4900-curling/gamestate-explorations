"""Geometry adapter for 640x360 split-screen 2024 source videos.

Each 320x360 panel is scaled 2x to the 640x720 analysis frame used by the
full-resolution split-panel camera registration. Upsampling adds no detail;
the method requires separate source validation before pipeline promotion.
"""

import cv2

try:
    from .split_panel_camera_registration import camera_relative_pair
except ImportError:
    from split_panel_camera_registration import camera_relative_pair


def panel_for_pixel(pixel):
    x, y = pixel
    if not (0 <= x < 640 and 0 <= y < 360):
        raise ValueError("Point outside 640x360 split-screen source")
    return 0 if x < 320 else 1


def panel_pixel(pixel, panel):
    if panel not in (0, 1) or panel_for_pixel(pixel) != panel:
        raise ValueError("Point does not belong to selected low-res panel")
    return ((pixel[0] - 320 * panel) * 2, pixel[1] * 2)


def resize_panel(frame, panel):
    if frame.shape[:2] != (360, 640):
        raise ValueError("Expected 640x360 split-screen source frame")
    if panel not in (0, 1):
        raise ValueError("Unknown panel")
    crop = frame[:, panel * 320 : (panel + 1) * 320]
    return cv2.resize(crop, (640, 720), interpolation=cv2.INTER_LINEAR)


def source_pair(before_pixel, after_pixel, before_time_s, after_time_s, frame_at):
    before_panel = panel_for_pixel(before_pixel)
    if panel_for_pixel(after_pixel) != before_panel:
        return {
            "status": "crosses_split_panel_boundary",
            "camera_residual_px": None,
            "subpairs": [],
        }

    def panel_frame(time_s):
        return resize_panel(frame_at(time_s), before_panel)

    result = camera_relative_pair(
        panel_pixel(before_pixel, before_panel),
        panel_pixel(after_pixel, before_panel),
        before_time_s,
        after_time_s,
        panel_frame,
    )
    return {
        **result,
        "panel": "left" if before_panel == 0 else "right",
        "coordinate_frame": "640x720_upsampled_360p_split_panel_pixels",
    }
