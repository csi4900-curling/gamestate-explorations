"""Compose short source-frame camera transforms without bridging failures."""

import numpy as np

try:
    from .camera_relative_motion import estimate_camera_transform
except ImportError:
    from camera_relative_motion import estimate_camera_transform


def composed_residual(
    before_pixel, after_pixel, before_time_s, after_time_s, frame_at, *, nominal_step_s=0.25
):
    """Return camera-relative displacement only if every subpair registers.

    `frame_at` supplies original 640x360 BGR frames for the requested source
    timestamps. A failed subpair cannot be interpolated by a later fit.
    """
    if after_time_s <= before_time_s or nominal_step_s <= 0:
        raise ValueError("Invalid frame-pair interval")
    interval = after_time_s - before_time_s
    steps = max(1, round(interval / nominal_step_s))
    times = [before_time_s + interval * index / steps for index in range(steps + 1)]
    matrix = np.eye(3)
    details = []
    frame = frame_at(times[0])
    for time in times[1:]:
        next_frame = frame_at(time)
        registration = estimate_camera_transform(frame, next_frame)
        details.append(
            {
                "interval_s": [round(times[len(details)], 4), round(time, 4)],
                "tracked_features": (registration["tracked_features"] if registration else 0),
                "inliers": registration["inliers"] if registration else 0,
                "inlier_fraction": (
                    round(registration["inlier_fraction"], 4) if registration else 0
                ),
                "reliable": bool(registration and registration["reliable"]),
            }
        )
        if registration is None or not registration["reliable"]:
            return {
                "status": "unregistered_subpair",
                "camera_residual_px": None,
                "subpairs": details,
            }
        transform = np.eye(3)
        transform[:2] = registration["matrix"]
        matrix = transform @ matrix
        frame = next_frame
    projected = matrix @ np.asarray([*before_pixel, 1], dtype=float)
    residual = np.linalg.norm(np.asarray(after_pixel, dtype=float) - projected[:2])
    return {
        "status": "all_subpairs_registered",
        "camera_residual_px": round(float(residual), 3),
        "subpairs": details,
    }
