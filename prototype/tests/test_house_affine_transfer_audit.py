"""A second image landmark can reject ellipse-only calibration transfer."""

import cv2
import numpy as np

from house_affine_transfer_audit import (affine_line_residual,
                                         summarize_residuals,
                                         transverse_line_y)


def test_detects_long_horizontal_marking_below_house():
    frame = np.full((360, 640, 3), 245, dtype=np.uint8)
    cv2.line(frame, (330, 215), (629, 215), (60, 60, 60), 2)
    result = transverse_line_y(frame, 153)
    assert 213 <= result["line_y_px"] <= 217


def test_affine_transfer_rejected_by_heldout_line_residual():
    reference = {"center_px": [485, 152], "axis_lengths_px": [256, 30]}
    target = {"center_px": [485, 182], "axis_lengths_px": [267, 30]}
    row = affine_line_residual(reference, 208, target, 247)
    assert row["observed_minus_predicted_px"] == 9
    assert summarize_residuals([row])["status"] == \
        "reject_simple_house_affine_transfer"


def test_empty_audit_abstains():
    assert summarize_residuals([])["status"] == "abstain_no_stable_house_samples"
