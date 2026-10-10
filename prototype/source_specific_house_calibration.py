"""Experimental per-frame rink-plane calibration from ring paint and hog line."""

import numpy as np
from scipy.optimize import least_squares

from house_affine_transfer_audit import transverse_line_y
from rectification_core import RADII, ring_edges, ring_summary, validate_rings
from vision_core import project


REGION = (320, 0, 640, 360)
HOG_FROM_TEE_M = 6.401


def initial_from_reference(reference_H_1080, reference_ellipse, target_ellipse):
    """Initialize from the tuned view; this transform itself failed transfer QA."""
    ref_x, ref_y = reference_ellipse["center_px"]
    x, y = target_ellipse["center_px"]
    sx = reference_ellipse["axis_lengths_px"][0] / target_ellipse["axis_lengths_px"][0]
    sy = reference_ellipse["axis_lengths_px"][1] / target_ellipse["axis_lengths_px"][1]
    target_to_ref = np.array([[sx, 0, ref_x - sx * x],
                              [0, sy, ref_y - sy * y], [0, 0, 1.]])
    H = np.asarray(reference_H_1080, float) @ np.diag([3., 3., 1.]) @ target_to_ref
    return H / H[2, 2]


def fit_source_house(frame, target_ellipse, reference_H_1080,
                     reference_ellipse):
    """Fit outer/middle paint and hog line; keep inner and angular samples out."""
    if frame.shape != (360, 640, 3):
        raise ValueError("Expected normalized 640x360 split frame")
    initial = initial_from_reference(reference_H_1080, reference_ellipse,
                                     target_ellipse)
    edges = [edge for radius in RADII[:2]
             for edge in ring_edges(frame, initial, radius, REGION, search_px=7)]
    train = [edge for edge in edges if int(edge["angle_deg"] // 3) % 4 != 0]
    held = [edge for edge in edges if int(edge["angle_deg"] // 3) % 4 == 0]
    inner = ring_edges(frame, initial, RADII[2], REGION, search_px=7)
    if len(train) < 70 or len(held) < 15:
        return None, {"status": "abstain_insufficient_ring_edges",
                      "training_edge_count": len(train),
                      "heldout_edge_count": len(held)}
    norm_pixels = np.array([[1 / 320, 0, -1], [0, 1 / 180, -1], [0, 0, 1.]])
    normalized_H = initial @ np.linalg.inv(norm_pixels)
    normalized_H /= normalized_H[2, 2]
    points = project(norm_pixels, [edge["pixel"] for edge in train])
    radii = np.array([edge["radius_m"] for edge in train])
    scale = np.array([edge["metres_per_normal_pixel"] for edge in train])
    line = transverse_line_y(frame, target_ellipse["center_px"][1])
    hog_pixels = np.array([[x, line["line_y_px"]] for x in (400, 490, 580)])
    cx, cy = target_ellipse["center_px"]
    prior_pixels = np.array([[cx, cy], [cx - 100, cy], [cx + 100, cy],
                             [cx, cy - 20], [cx, cy + 20]])
    prior_world = project(initial, prior_pixels)

    def unpack(parameters):
        return np.r_[parameters, 1.].reshape(3, 3)

    def residual(parameters):
        H = unpack(parameters) @ norm_pixels
        ring = (np.linalg.norm(project(unpack(parameters), points), axis=1)
                - radii) / scale
        hog = (project(H, hog_pixels)[:, 1] - HOG_FROM_TEE_M) / .10
        prior = ((project(H, prior_pixels) - prior_world) / .15).ravel()
        return np.r_[ring, hog, prior]

    result = least_squares(residual, normalized_H.ravel()[:8],
                           loss="soft_l1", f_scale=1., max_nfev=100,
                           x_scale="jac")
    H = unpack(result.x) @ norm_pixels
    H /= H[2, 2]
    if not result.success or not np.isfinite(H).all():
        return None, {"status": "abstain_fit_did_not_converge",
                      "optimizer_message": result.message}
    middle_supported, middle_check = validate_rings(frame, H, REGION)
    held_summary = ring_summary(H, held)
    inner_summary = ring_summary(H, inner)
    hog_world = project(H, hog_pixels)[:, 1]
    geometry_points = project(H, [[cx - 100, cy], [cx, cy], [cx + 100, cy],
                                  [cx, cy + 20]])
    monotonic = (geometry_points[0, 0] < geometry_points[1, 0] <
                 geometry_points[2, 0] and
                 geometry_points[3, 1] > geometry_points[1, 1])
    accepted = (middle_supported and monotonic and len(inner) >= 40 and
                held_summary["p95_abs_radial_error_m"] < .26 and
                inner_summary["p95_abs_radial_error_m"] < .25 and
                float(np.max(np.abs(hog_world - HOG_FROM_TEE_M))) < .15)
    diagnostic = {
        "status": ("conditional_image_evidence_supported" if accepted else
                   "abstain_geometry_checks_failed"),
        "initial_H": initial.tolist(),
        "fitted_H": H.tolist(),
        "training_ring": ring_summary(H, train),
        "heldout_outer_middle_ring": held_summary,
        "withheld_inner_ring": inner_summary,
        "middle_frame_ring_check": middle_check,
        "hog_line_y_px": line["line_y_px"],
        "hog_world_y_m_at_three_pixels": [round(float(y), 4) for y in hog_world],
        "monotonic_orientation": bool(monotonic),
        "optimizer_evaluations": result.nfev,
        "metric_accuracy_validated": False,
        "stone_ground_contact_verified": False,
    }
    return H if accepted else None, diagnostic
