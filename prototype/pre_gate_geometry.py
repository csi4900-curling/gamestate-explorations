"""Image-space straight-path checks, without assuming uniform speed or metric truth."""

import numpy as np


def line_fit(points):
    p = np.asarray(points, float)
    if p.ndim != 2 or p.shape[1] != 2 or len(p) < 3 or not np.isfinite(p).all():
        raise ValueError("Need at least three finite 2D points")
    centre = p.mean(axis=0)
    _, s, vt = np.linalg.svd(p - centre, full_matrices=False)
    if s[0] < 1e-8:
        raise ValueError("No measurable displacement")
    normal = vt[-1]
    residual = (p - centre) @ normal
    return {
        "centre": centre.tolist(),
        "normal": normal.tolist(),
        "rms_px": float(np.sqrt(np.mean(residual**2))),
        "max_px": float(np.max(np.abs(residual))),
        "residuals_px": residual.tolist(),
    }


def audit_path(points):
    p = np.asarray(points, float)
    fit = line_fit(p)
    direction = p[-1] - p[0]
    span = float(np.linalg.norm(direction))
    if span < 1e-8:
        raise ValueError("Coincident endpoints")
    normal = np.array([-direction[1], direction[0]]) / span
    errors = (p - p[0]) @ normal
    held = None
    if len(p) >= 8:
        n = int(np.floor(2 * len(p) / 3))
        train = line_fit(p[:n])
        held_errors = (p[n:] - train["centre"]) @ np.array(train["normal"])
        held = {
            "train_count": n,
            "test_count": len(p) - n,
            "rms_px": float(np.sqrt(np.mean(held_errors**2))),
            "max_px": float(np.max(np.abs(held_errors))),
            "fit": train,
        }
    return {
        "best_fit": fit,
        "endpoint_line": {
            "rms_px": float(np.sqrt(np.mean(errors**2))),
            "max_px": float(np.max(np.abs(errors))),
            "residuals_px": errors.tolist(),
        },
        "observed_span_px": span,
        "held_out_later_points": held,
    }
