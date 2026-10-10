"""Image-only alignment check using the stationary blue house paint."""

import cv2
import numpy as np


ROI_XYXY = (340, 160, 620, 200)


def blue_house_mask(frame):
    if frame.shape[:2] != (360, 640):
        raise ValueError("Expected 640x360 broadcast frame")
    x0, y0, x1, y1 = ROI_XYXY
    hue, saturation, value = cv2.split(
        cv2.cvtColor(frame[y0:y1, x0:x1], cv2.COLOR_BGR2HSV))
    return ((hue >= 90) & (hue <= 135) &
            (saturation >= 45) & (value >= 45)).astype(np.uint8)


def alignment_probe(first_mask, second_mask, *, max_shift_px=8):
    if first_mask.shape != second_mask.shape or first_mask.ndim != 2:
        raise ValueError("House masks must have equal 2D shape")
    if max_shift_px < 0:
        raise ValueError("Invalid shift range")
    if not np.any(first_mask) or not np.any(second_mask):
        raise ValueError("Empty painted-house mask")
    first = (first_mask != 0).astype(np.uint8)
    second = (second_mask != 0).astype(np.uint8)
    scores = []
    height, width = first.shape
    for dy in range(-max_shift_px, max_shift_px + 1):
        for dx in range(-max_shift_px, max_shift_px + 1):
            shifted = cv2.warpAffine(
                second, np.float32([[1, 0, dx], [0, 1, dy]]),
                (width, height), flags=cv2.INTER_NEAREST)
            intersection = int(np.count_nonzero(first & shifted))
            union = int(np.count_nonzero(first | shifted))
            scores.append((intersection / union, dx, dy))
    best = max(scores, key=lambda item: item[0])
    zero = next(score for score in scores if score[1:] == (0, 0))
    return {
        "first_blue_px": int(np.count_nonzero(first)),
        "second_blue_px": int(np.count_nonzero(second)),
        "best_translation_second_to_first_px": [best[1], best[2]],
        "best_mask_iou": round(best[0], 4),
        "zero_translation_mask_iou": round(zero[0], 4),
        "zero_translation_is_best": best[1:] == (0, 0),
        "full_camera_pose_verified": False,
    }
