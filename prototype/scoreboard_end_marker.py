"""Read the active-end chevron in the 2024 WWhCC 640x360 broadcast graphic.

Returns no observation when the graphic is absent, occluded, or ambiguous.
The graphic may update after an end's first delivery, so its transitions are
not physical end-boundary timestamps.
"""

import cv2
import numpy as np


# Binary shape sampled from a clear China frame at 500 s. The same template
# and thresholds are frozen for transfer to the other 2024 recordings.
ARROW = np.array(
    [
        [0, 0, 0, 0, 1, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 1, 1, 0, 0],
        [0, 0, 0, 0, 0, 1, 1, 1, 0],
        [0, 0, 0, 0, 1, 1, 1, 1, 0],
        [0, 0, 0, 1, 1, 0, 0, 0, 0],
        [0, 0, 1, 1, 0, 0, 0, 0, 0],
        [0, 1, 1, 0, 0, 0, 0, 0, 0],
        [0, 1, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 0, 0],
    ],
    dtype=np.uint8,
)


def panel_shift_evidence(frame, *, min_fraction=0.35):
    """Find horizontal graphic shift from paired red/yellow team panels."""
    if frame is None or frame.ndim != 3 or frame.shape[2] != 3:
        raise ValueError("Expected a BGR frame")
    hsv = cv2.cvtColor(
        cv2.resize(frame, (640, 360), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2HSV
    )
    candidates = []
    for shift in range(-5, 46):
        x = 364 + shift
        red = hsv[53:65, x : x + 30]
        yellow = hsv[66:79, x : x + 30]
        red_fraction = np.mean(
            (
                ((red[:, :, 0] < 12) | (red[:, :, 0] > 170))
                & (red[:, :, 1] > 75)
                & (red[:, :, 2] > 60)
            )
        )
        yellow_fraction = np.mean(
            (
                (yellow[:, :, 0] > 15)
                & (yellow[:, :, 0] < 45)
                & (yellow[:, :, 1] > 75)
                & (yellow[:, :, 2] > 70)
            )
        )
        candidates.append((min(red_fraction, yellow_fraction), shift))
    score, shift = max(candidates)
    return {"shift_px": shift, "score": round(float(score), 3)} if score > min_fraction else None


def fit_header_grid(frames, panel_shift_px, *, min_edge_score=20.0):
    """Fit scoreboard column origin and pitch from persistent header edges."""
    if len(frames) < 5:
        return None
    profiles = []
    for frame in frames:
        if frame is None or frame.ndim != 3 or frame.shape[2] != 3:
            raise ValueError("Expected BGR frames")
        gray = cv2.cvtColor(
            cv2.resize(frame, (640, 360), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2GRAY
        ).astype(np.float32)
        profiles.append(np.abs(np.diff(gray[39:53], axis=1)).mean(axis=0))
    profile = np.median(profiles, axis=0)
    best = (0.0, None, None)
    for base in np.arange(395 + panel_shift_px, 404 + panel_shift_px, 0.5):
        for pitch in np.arange(8.5, 11.01, 0.1):
            columns = [round(base + index * pitch) for index in range(10)]
            score = float(np.mean(profile[columns]))
            if score > best[0]:
                best = (score, base, pitch)
    score, base, pitch = best
    if score < min_edge_score:
        return None
    return {
        "header_base_x_px": round(float(base), 2),
        "arrow_origin_x_px": round(float(base - 3)),
        "slot_pitch_px": round(float(pitch), 2),
        "edge_score": round(score, 2),
    }


def read_active_end_marker(
    frame,
    *,
    x_shift_px=0,
    slot_pitch_px=10.3,
    position_tolerance_px=2,
    min_similarity=0.90,
    min_margin=0.04,
):
    """Return {end, colour, similarity, margin} or None for an unsupported view."""
    if frame is None or frame.ndim != 3 or frame.shape[2] != 3:
        raise ValueError("Expected a BGR frame")
    gray = cv2.cvtColor(
        cv2.resize(frame, (640, 360), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2GRAY
    )
    hits = []
    for end in range(1, 9):
        x0 = 399 + x_shift_px + round((end - 1) * slot_pitch_px)
        for colour, y0 in (("red", 53), ("yellow", 68)):
            best = 0.0
            for dx in range(-position_tolerance_px, position_tolerance_px + 1):
                for dy in range(-7, 8):
                    patch = gray[y0 + dy : y0 + dy + 10, x0 + dx : x0 + dx + 9]
                    dark = patch < 150
                    similarity = 1.0 - np.count_nonzero(dark != ARROW) / ARROW.size
                    best = max(best, similarity)
            hits.append((best, end, colour))
    hits.sort(reverse=True)
    (score, end, colour), (runner_up, _, _) = hits[:2]
    margin = score - runner_up
    if score < min_similarity or margin < min_margin:
        return None
    return {
        "end": end,
        "colour": colour,
        "similarity": round(float(score), 3),
        "margin": round(float(margin), 3),
    }
