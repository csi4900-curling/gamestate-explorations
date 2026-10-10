"""Visual corroboration for the last delivery when a broadcast counter persists.

Only called with an externally observed one-stone-remaining state. A coloured
cap needs a neutral granite surround, white ice nearby, and sustained movement.
This is a narrow fallback, not a general full-frame throw detector.
"""

import cv2
import numpy as np
from bisect import bisect_right

try:
    from .scene_cuts import scene_cut_evidence
except ImportError:  # Scripts also import this module from the prototype directory.
    from scene_cuts import scene_cut_evidence


def stone_cap_candidates(frame, colour, *, allow_bright_body=False, allow_large_caps=False):
    if colour not in ("red", "yellow"):
        raise ValueError("Unsupported stone colour")
    if frame is None or frame.ndim != 3 or frame.shape[2] != 3:
        raise ValueError("Expected BGR frame")
    image = cv2.resize(frame, (640, 360), interpolation=cv2.INTER_AREA)
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    hue, saturation, value = cv2.split(hsv)
    if colour == "red":
        mask = ((hue < 12) | (hue > 170)) & (saturation > 85) & (value > 50)
    else:
        mask = (hue > 16) & (hue < 43) & (saturation > 85) & (value > 70)
    mask[:70] = False  # Exclude the television graphic.
    contours, _ = cv2.findContours(
        mask.astype("uint8") * 255, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )
    candidates = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        area = cv2.contourArea(contour)
        max_area, max_width, max_height = (4000, 160, 80) if allow_large_caps else (500, 35, 30)
        if not (30 <= area <= max_area and 8 <= w <= max_width and 4 <= h <= max_height):
            continue
        x0, x1 = max(0, x - 6), min(640, x + w + 6)
        y0, y1 = max(0, y - 6), min(360, y + h + 6)
        patch = hsv[y0:y1, x0:x1]
        outside = np.ones(patch.shape[:2], dtype=bool)
        outside[y - y0 : y + h - y0, x - x0 : x + w - x0] = False
        if not outside.any():
            continue
        neutral = (patch[:, :, 1] < 90) & (patch[:, :, 2] > 40) & (patch[:, :, 2] < 190)
        ice = (patch[:, :, 1] < 95) & (patch[:, :, 2] > 150)
        neutral_fraction = float(neutral[outside].mean())
        ice_fraction = float(ice[outside].mean())
        # Experimental gap probe: a bright stone body can resemble ice in
        # overhead views. Keep the stricter historical rule as the default.
        if ice_fraction < 0.45 or (
            neutral_fraction < 0.30 and not (allow_bright_body and ice_fraction >= 0.65)
        ):
            continue
        candidates.append(
            {
                "pixel": [x + w / 2, y + h / 2],
                "bbox": [x, y, w, h],
                "cap_area_px2": area,
                "neutral_surround_fraction": neutral_fraction,
                "white_ice_fraction": ice_fraction,
            }
        )
    return candidates


def moving_cap_tracks(observations, *, max_gap_s=2.0, max_step_px=25.0, cut_times_s=()):
    """Greedy short-track association, returning only sustained motion evidence."""
    tracks = []
    cuts = sorted(cut_times_s)
    for t, candidates in observations:
        used = set()
        for track in tracks:
            previous = track[-1]
            gap = t - previous["time_s"]
            if not 0 < gap <= max_gap_s:
                continue
            # A coordinate match across a broadcast edit is not object identity.
            cut_index = bisect_right(cuts, previous["time_s"])
            if cut_index < len(cuts) and cuts[cut_index] <= t:
                continue
            choices = [
                (np.linalg.norm(np.subtract(c["pixel"], previous["pixel"])), j)
                for j, c in enumerate(candidates)
                if j not in used
            ]
            if not choices:
                continue
            distance, index = min(choices)
            if distance <= max_step_px * gap:
                track.append(dict(candidates[index], time_s=t))
                used.add(index)
        for j, candidate in enumerate(candidates):
            if j not in used:
                tracks.append([dict(candidate, time_s=t)])
    supported = []
    for points in tracks:
        if len(points) < 4 or points[-1]["time_s"] - points[0]["time_s"] < 3:
            continue
        xy = np.asarray([p["pixel"] for p in points], float)
        span = float(np.max(np.linalg.norm(xy - xy[0], axis=1)))
        if span < 25:
            continue
        supported.append({"points": points, "span_px": span})
    return sorted(supported, key=lambda track: (-len(track["points"]), -track["span_px"]))


def verify_stone_motion_in_interval(
    capture, fps, *, colour, start_s, end_s, detect_hard_cuts=False
):
    """Search a declared interval and confirm only one supported colour track."""
    start = max(0, int(start_s))
    end = int(end_s)
    if end <= start:
        raise ValueError("Empty visual search interval")
    observations = []
    cut_times = []
    previous_frame = None
    for t in range(start, end):
        capture.set(cv2.CAP_PROP_POS_FRAMES, round(t * fps))
        ok, frame = capture.read()
        if not ok:
            raise RuntimeError(f"Frame decode failed at {t} seconds")
        if detect_hard_cuts and previous_frame is not None:
            if scene_cut_evidence(previous_frame, frame)["hard_cut"]:
                cut_times.append(float(t))
        observations.append((float(t), stone_cap_candidates(frame, colour)))
        previous_frame = frame
    tracks = moving_cap_tracks(observations, cut_times_s=cut_times)
    return {
        "search_interval_s": [start, end],
        "hard_cut_times_s": cut_times,
        "tracks": tracks,
        "selected_track": tracks[0] if len(tracks) == 1 else None,
    }


def verify_final_stone_motion(capture, fps, *, colour, anchor_s, source_end_s):
    """Search near a one-stone counter state; return observed tracks and choice."""
    return verify_stone_motion_in_interval(
        capture,
        fps,
        colour=colour,
        start_s=max(0, int(anchor_s) - 5),
        end_s=min(int(source_end_s), int(anchor_s) + 36),
    )
