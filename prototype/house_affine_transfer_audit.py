"""Test whether a house-ellipse affine transfer preserves another rink line."""

from statistics import median

import cv2
import numpy as np


LINE_XY_RANGE = (330, 630)
LINE_OFFSET_FROM_HOUSE_CENTER_PX = (40, 80)


def transverse_line_y(frame, center_y):
    """Strongest long horizontal image edge below the visible house."""
    gray = cv2.cvtColor(frame[:, LINE_XY_RANGE[0]:LINE_XY_RANGE[1]],
                        cv2.COLOR_BGR2GRAY)
    horizontal = np.abs(cv2.Sobel(gray, cv2.CV_32F, 0, 1)).mean(axis=1)
    start = round(center_y + LINE_OFFSET_FROM_HOUSE_CENTER_PX[0])
    end = round(center_y + LINE_OFFSET_FROM_HOUSE_CENTER_PX[1])
    if start < 0 or end > len(horizontal) or start >= end:
        raise ValueError("Transverse-line search lies outside source frame")
    index = start + int(np.argmax(horizontal[start:end]))
    return {"line_y_px": index,
            "mean_vertical_edge_strength": round(float(horizontal[index]), 2)}


def affine_line_residual(reference_ellipse, reference_line_y,
                         target_ellipse, target_line_y):
    """Transfer only image-center/vertical-scale; residual is an image diagnostic."""
    ref_center = reference_ellipse["center_px"][1]
    ref_minor = reference_ellipse["axis_lengths_px"][1]
    target_center = target_ellipse["center_px"][1]
    target_minor = target_ellipse["axis_lengths_px"][1]
    predicted = target_center + (reference_line_y - ref_center) * (
        target_minor / ref_minor)
    return {"predicted_line_y_px": round(predicted, 3),
            "observed_line_y_px": target_line_y,
            "observed_minus_predicted_px": round(target_line_y - predicted, 3)}


def summarize_residuals(rows, *, max_median_abs_px=4):
    if not rows:
        return {"status": "abstain_no_stable_house_samples",
                "sample_count": 0, "median_abs_residual_px": None}
    residuals = [row["observed_minus_predicted_px"] for row in rows]
    absolute = sorted(abs(value) for value in residuals)
    median_abs = round(median(absolute), 3)
    return {
        "status": ("reject_simple_house_affine_transfer" if median_abs > max_median_abs_px
                   else "line_check_passes_not_metric_calibration"),
        "sample_count": len(rows),
        "median_signed_residual_px": round(median(residuals), 3),
        "median_abs_residual_px": median_abs,
        "p95_abs_residual_px": round(absolute[round(.95 * (len(absolute) - 1))], 3),
        "max_median_abs_residual_px": max_median_abs_px,
    }
