"""Source-specific plane calibration must abstain without ring evidence."""

import numpy as np

from source_specific_house_calibration import fit_source_house, initial_from_reference


def ellipse(cx=485, cy=152):
    return {"center_px": [cx, cy], "axis_lengths_px": [256, 30]}


def test_same_ellipse_keeps_reference_projection_after_resize():
    H = np.array([[0.01, 0, -5], [0, 0.02, -3], [0, 0, 1.0]])
    initial = initial_from_reference(H, ellipse(), ellipse())
    assert np.allclose(initial, H @ np.diag([3.0, 3.0, 1.0]))


def test_blank_frame_abstains_without_fabricating_calibration():
    frame = np.full((360, 640, 3), 245, dtype=np.uint8)
    H = np.array([[0.01, 0, -5], [0, 0.02, -3], [0, 0, 1.0]])
    result, diagnostic = fit_source_house(frame, ellipse(), H, ellipse())
    assert result is None
    assert diagnostic["status"] == "abstain_insufficient_ring_edges"
