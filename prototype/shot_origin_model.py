"""Compact spatial appearance features for an experimental delivery-view model."""

import cv2
import numpy as np

from learned_gap_confirmation import compact_overlay_visible


def frame_features(frame):
    """Describe ice, rink markings and player colors by image region."""
    image = cv2.resize(frame, (160, 90), interpolation=cv2.INTER_AREA)
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    h, s, v = cv2.split(hsv)
    masks = [
        (s < 95) & (v > 150),  # ice
        (h > 90) & (h < 135) & (s > 60) & (v < 180),  # rink blue
        ((h < 12) | (h > 170)) & (s > 85) & (v > 50),  # red clothing/stone
        (h > 16) & (h < 43) & (s > 85) & (v > 70),  # yellow clothing/stone
        (v < 70),  # wheels, shadows, graphic
    ]
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0)
    gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1)
    masks.append(np.sqrt(gx * gx + gy * gy) > 45)
    grid = [cv2.resize(mask.astype(np.float32), (8, 5),
                       interpolation=cv2.INTER_AREA).ravel() for mask in masks]
    return np.concatenate([*grid, [float(compact_overlay_visible(frame))]]).astype(np.float32)


def shot_features(frames):
    if len(frames) != 3:
        raise ValueError("Three source frames per shot are required")
    features = np.stack([frame_features(frame) for frame in frames])
    return np.concatenate((features.mean(axis=0), features.std(axis=0))).astype(np.float32)
