"""Route camera-relative motion only through a matching source-layout run.

Times are local to the supplied video file. An excerpt with global event
timestamps must subtract its source offset before using this API.
"""

from hashlib import sha256
from pathlib import Path

try:
    from .ice_region_camera_registration import ice_region_composed_residual
    from . import lowres_split_panel_camera_registration as lowres_split
    from .split_panel_camera_registration import (
        camera_relative_pair,
        panel_for_pixel,
        panel_pixel,
        resize_panel,
    )
except ImportError:
    from ice_region_camera_registration import ice_region_composed_residual
    import lowres_split_panel_camera_registration as lowres_split
    from split_panel_camera_registration import (
        camera_relative_pair,
        panel_for_pixel,
        panel_pixel,
        resize_panel,
    )


LAYOUT_CODE = Path(__file__).with_name("layout_preflight.py")


def _abstain(reason, *, layout=None, panel=None):
    return {
        "status": reason,
        "layout": layout,
        "panel": panel,
        "camera_residual_px": None,
        "subpairs": [],
    }


def source_camera_relative_pair(
    preflight, source_sha256, before_pixel, after_pixel, before_time_s, after_time_s, frame_at
):
    """Measure one pair within a verified 2022 or 2024 layout run.

    `preflight` comes from `run_throw_pipeline.py --preflight-only` for this
    exact video file. `frame_at` decodes a BGR frame at a video-local time.
    The result always states a layout and coordinate frame or why it abstained.
    """
    if before_time_s >= after_time_s:
        raise ValueError("Frame-pair times must increase")
    if (
        preflight.get("source_sha256") != source_sha256
        or preflight.get("preflight_sha256") != sha256(LAYOUT_CODE.read_bytes()).hexdigest()
    ):
        raise ValueError("Preflight source or layout-code hash differs")
    start, end = preflight["source_interval_s"]
    if not start <= before_time_s < after_time_s <= end:
        return _abstain("outside_preflight_interval")
    candidates = [
        run
        for run in preflight["runs"]
        if run["interval_s"][0] <= before_time_s and after_time_s <= run["interval_s"][1]
    ]
    if len(candidates) != 1:
        return _abstain("crosses_layout_run_boundary")
    layout = candidates[0]["layout"]
    if layout not in ("beijing_2022", "split_2024"):
        return _abstain("unsupported_layout_run", layout=layout)
    first = frame_at(before_time_s)
    if layout == "beijing_2022":
        if first.shape[:2] != (360, 640):
            return _abstain("unsupported_resolution_for_layout", layout=layout)
        if not all(0 <= p[0] < 640 and 0 <= p[1] < 360 for p in (before_pixel, after_pixel)):
            return _abstain("point_outside_view", layout=layout)

        def checked_frame(time_s):
            frame = first if time_s == before_time_s else frame_at(time_s)
            if frame.shape[:2] != (360, 640):
                raise ValueError("Frame shape changed within Beijing layout pair")
            return frame

        result = ice_region_composed_residual(
            before_pixel, after_pixel, before_time_s, after_time_s, checked_frame
        )
        return {
            **result,
            "layout": layout,
            "panel": None,
            "coordinate_frame": "640x360_single_source_pixels",
        }
    if first.shape[:2] == (360, 640):
        try:
            before_panel = lowres_split.panel_for_pixel(before_pixel)
            after_panel = lowres_split.panel_for_pixel(after_pixel)
        except ValueError:
            return _abstain("point_outside_view", layout=layout)
        if before_panel != after_panel:
            return _abstain("crosses_split_panel_boundary", layout=layout)

        def checked_lowres_frame(time_s):
            frame = first if time_s == before_time_s else frame_at(time_s)
            if frame.shape[:2] != (360, 640):
                raise ValueError("Frame shape changed within split layout pair")
            return frame

        result = lowres_split.source_pair(
            before_pixel, after_pixel, before_time_s, after_time_s, checked_lowres_frame
        )
        return {**result, "layout": layout}
    if first.shape[:2] != (1080, 1920):
        return _abstain("unsupported_resolution_for_layout", layout=layout)
    try:
        before_panel = panel_for_pixel(before_pixel)
        after_panel = panel_for_pixel(after_pixel)
    except ValueError:
        return _abstain("point_outside_view", layout=layout)
    if before_panel != after_panel:
        return _abstain("crosses_split_panel_boundary", layout=layout)

    def checked_panel_frame(time_s):
        frame = first if time_s == before_time_s else frame_at(time_s)
        if frame.shape[:2] != (1080, 1920):
            raise ValueError("Frame shape changed within split layout pair")
        return resize_panel(frame, before_panel)

    result = camera_relative_pair(
        panel_pixel(before_pixel, before_panel),
        panel_pixel(after_pixel, before_panel),
        before_time_s,
        after_time_s,
        checked_panel_frame,
    )
    return {
        **result,
        "layout": layout,
        "panel": "left" if before_panel == 0 else "right",
        "coordinate_frame": "640x720_aspect_preserved_panel_pixels",
    }
