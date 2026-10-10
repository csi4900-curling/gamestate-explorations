"""Score coloured-cap candidates with the frozen broadcast context model.

This verifies a visual stone-like patch. It does not decide whether the stone
was delivered, moving, or linked across a camera cut.
"""

import cv2
import numpy as np

from stone_patch_detector import patch_features


def context_bbox(cap_bbox):
    """Match the context geometry used by build_cap_patch_review.py."""
    x, y, width, height = cap_bbox
    side = max(48, min(210, round(3.0 * max(width, height))))
    center_x = x + width / 2
    center_y = y + height / 2 + side * 0.13
    return [round(center_x - side / 2), round(center_y - side / 2), side, side]


def score_candidates(frame, candidates, model):
    """Return cap candidates with a frozen context-patch score and decision."""
    if not candidates:
        return []
    image = cv2.resize(frame, (640, 360), interpolation=cv2.INTER_AREA)
    features = np.stack([patch_features(image, context_bbox(row["bbox"])) for row in candidates])
    scores = ((features - model["mean"]) / model["scale"]) @ model["weights"].ravel()
    scores += model["intercept"].item()
    threshold = float(model["threshold"])
    return [
        dict(row, patch_score=float(score), patch_accepted=bool(score >= threshold))
        for row, score in zip(candidates, scores)
    ]
