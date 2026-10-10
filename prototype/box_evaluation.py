"""One-to-one same-colour bounding-box scoring; pixel/metric centres are not scored."""

import numpy as np
from end_evaluation import assign


def iou(a, b):
    x, y, w, h = a
    xx, yy, ww, hh = b
    overlap = max(0, min(x + w, xx + ww) - max(x, xx)) * max(0, min(y + h, yy + hh) - max(y, yy))
    union = w * h + ww * hh - overlap
    return overlap / union if union > 0 else 0.0


def score_boxes(reference, predicted, threshold=0.5):
    overlap = np.array([[iou(r["bbox"], p["bbox"]) for p in predicted] for r in reference]).reshape(
        len(reference), len(predicted)
    )
    colours = np.array(
        [[r["colour"] == p["colour"] for p in predicted] for r in reference], dtype=bool
    ).reshape(overlap.shape)
    pairs = assign(1 - overlap, (overlap >= threshold) & colours)
    return {
        "references": len(reference),
        "predictions": len(predicted),
        "matches": len(pairs),
        "misses": len(reference) - len(pairs),
        "extras": len(predicted) - len(pairs),
        "matched_ious": [float(overlap[i, j]) for i, j in pairs],
    }
