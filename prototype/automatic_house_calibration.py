"""Per-image house calibration from concentric paint, without match labels.

Axes are image-aligned local axes, not a resolved canonical rink orientation.
Outer and middle paint fit the homography; inner paint is withheld from fitting.
"""

import cv2
import numpy as np
from scipy.optimize import least_squares
from rectification_core import RADII, ring_edges, ring_summary, validate_rings
from vision_core import project


def calibrate_house(frame, region=None):
    h, w = frame.shape[:2]
    region = region or (0, 70, w, h)
    x0, y0, x1, y1 = region
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, (85, 65, 45), (135, 255, 255))
    valid = np.zeros_like(mask)
    valid[y0:y1, x0:x1] = 255
    mask &= valid
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    attempts = []
    for contour in sorted(contours, key=cv2.contourArea, reverse=True)[:6]:
        if len(contour) < 25 or cv2.contourArea(contour) < 450:
            continue
        (cx, cy), (a, b), angle = cv2.fitEllipse(contour)
        if min(a, b) < 16 or max(a, b) < 70 or max(a, b) > 1.8 * w:
            continue
        theta = np.deg2rad(angle)
        R = np.array([[np.cos(theta), -np.sin(theta)], [np.sin(theta), np.cos(theta)]])
        # Symmetric inverse square root retains image-right/image-down orientation.
        M = R @ np.diag([2 * RADII[0] / a, 2 * RADII[0] / b]) @ R.T
        initial = np.eye(3)
        initial[:2, :2] = M
        initial[:2, 2] = -M @ [cx, cy]
        edges = [
            e
            for radius in RADII[:2]
            for e in ring_edges(frame, initial, radius, region, search_px=8)
        ]
        train = [e for e in edges if int(e["angle_deg"] // 3) % 4]
        held = [e for e in edges if not int(e["angle_deg"] // 3) % 4]
        if len(train) < 65 or len(held) < 18:
            continue
        N = np.array([[1 / w, 0, -0.5], [0, 1 / h, -0.5], [0, 0, 1.0]])
        norm = initial @ np.linalg.inv(N)
        norm /= norm[2, 2]
        pts = project(N, [e["pixel"] for e in train])
        radii = np.array([e["radius_m"] for e in train])
        scales = np.array([e["metres_per_normal_pixel"] for e in train])

        def unpack(p):
            return np.r_[p, 1.0].reshape(3, 3)

        def residual(p):
            H = unpack(p)
            try:
                error = (np.linalg.norm(project(H, pts), axis=1) - radii) / scales
                # Fix the otherwise unidentifiable in-plane rotation, not shape.
                rot = (H[0, 1] - H[1, 0] * h / w) - (norm[0, 1] - norm[1, 0] * h / w)
                return np.r_[error, rot * 10]
            except ValueError:
                return np.full(len(pts) + 1, 1e6)

        opt = least_squares(residual, norm.ravel()[:8], loss="soft_l1", max_nfev=80, x_scale="jac")
        H = unpack(opt.x) @ N
        if not opt.success or not np.isfinite(H).all() or abs(np.linalg.det(H)) < 1e-12:
            continue
        inner = ring_edges(frame, initial, RADII[2], region, search_px=8)
        check = ring_summary(H, inner)
        hold = ring_summary(H, held)
        passed, rings = validate_rings(frame, H, region)
        diag = {
            "status": "ring_fit_rejected",
            "ring_check": rings,
            "withheld_inner": check,
            "heldout_angles": hold,
            "center_px": [cx, cy],
            "axis_semantics": "image_aligned_local_not_canonical_rink",
        }
        attempts.append(diag)
        if (
            passed
            and len(inner) >= 25
            and check["angular_bins"] >= 7
            and check["p95_abs_radial_error_m"] < 0.15
            and hold["p95_abs_radial_error_m"] < 0.15
        ):
            diag["status"] = "image_supported_automatic_house"
            return H / H[2, 2], diag
    return None, {"status": "no_supported_house_calibration", "attempts": attempts}
