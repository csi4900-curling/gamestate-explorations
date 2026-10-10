"""Attach camera-relative displacement to a span proposal's observed path."""

from layout_camera_motion import source_camera_relative_pair


def measure_candidate(event, preflight, source_sha256, frame_at):
    points = event.get("observed_track_points") or []
    if len(points) < 2:
        return {"id": event["id"], "status": "no_observed_track_path", "camera_residual_px": None}
    times = [point["time_s"] for point in points]
    if any(right <= left for left, right in zip(times, times[1:])):
        raise ValueError("Observed track times must increase")
    first, last = points[0], points[-1]
    frame = frame_at(first["time_s"])
    height, width = frame.shape[:2]
    if (width, height) not in ((640, 360), (1920, 1080)):
        return {
            "id": event["id"],
            "status": "unsupported_source_resolution",
            "camera_residual_px": None,
        }
    scale = width / 640
    pixels = [[v * scale for v in point["pixel"]] for point in (first, last)]
    result = source_camera_relative_pair(
        preflight, source_sha256, pixels[0], pixels[1], times[0], times[-1], frame_at
    )
    return {
        "id": event["id"],
        "observed_interval_s": [times[0], times[-1]],
        "source_pixels": pixels,
        "observed_point_count": len(points),
        **result,
    }
