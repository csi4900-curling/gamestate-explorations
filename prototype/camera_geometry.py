"""Transfer a measured ice-plane homography through estimated same-shot image motion.

No transform is copied by time alone. Every propagated result needs at least four inlier
feature correspondences and a finite, orientation-preserving homography.
"""

import cv2
import numpy as np
from automatic_house_calibration import calibrate_house
from rectification_core import RADII, ring_edges, ring_summary
from vision_core import project


def features(frame, region, *, strategy="baseline"):
    if strategy not in ("baseline", "adaptive_lmeds"):
        raise ValueError("Unknown registration strategy")
    x0, y0, x1, y1 = region
    mask = np.zeros(frame.shape[:2], np.uint8)
    if strategy == "adaptive_lmeds":
        mask[y0:y1, x0:x1] = 255
        sift = cv2.SIFT_create()
    else:
        # Preserved baseline: candidate replacement has not passed promotion checks.
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        ice = (hsv[:, :, 2] > 110) & ((hsv[:, :, 1] < 110) | ((hsv[:, :, 0] > 85) & (hsv[:, :, 0] < 135)))
        mask[y0:y1, x0:x1] = ice[y0:y1, x0:x1] * 255
        sift = cv2.SIFT_create(nfeatures=1800, contrastThreshold=0.01)
    kp, desc = sift.detectAndCompute(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), mask)
    return kp, desc


def transfer(reference, current, H, region, reference_features=None, current_features=None, *, strategy="baseline", model="projective"):
    if model not in ("projective", "similarity"):
        raise ValueError("Unknown camera motion model")
    if strategy not in ("baseline", "adaptive_lmeds"):
        raise ValueError("Unknown registration strategy")
    ka, da = reference_features or features(reference, region, strategy=strategy)
    kb, db = current_features or features(current, region, strategy=strategy)
    if da is None or db is None:
        return None, {"status": "no_registration_features"}
    if strategy == "adaptive_lmeds":
        good = cv2.BFMatcher(cv2.NORM_L2, crossCheck=True).match(da, db)
    else:
        pairs = cv2.BFMatcher().knnMatch(da, db, k=2)
        good = [m for pair in pairs if len(pair) == 2 for m,n in [pair] if m.distance < .7*n.distance]
    if len(good) < 4:
        return None, {"status": "insufficient_registration_matches", "matches": len(good)}
    a = np.array([ka[m.queryIdx].pt for m in good], np.float32)
    b = np.array([kb[m.trainIdx].pt for m in good], np.float32)
    if model == "similarity":
        A, mask = cv2.estimateAffinePartial2D(a, b, method=cv2.RANSAC,
                                            ransacReprojThreshold=1.5, maxIters=2000,
                                            confidence=.995)
        if A is not None:
            A = np.vstack([A, [0., 0., 1.]])
    elif strategy == "adaptive_lmeds":
        A, mask = cv2.findHomography(a, b, cv2.LMEDS)
    else:
        A, mask = cv2.findHomography(a, b, cv2.RANSAC, 1.5, maxIters=2000, confidence=0.995)
    if A is None:
        return None, {"status": "registration_fit_failed"}
    inside = mask.ravel().astype(bool)
    n = int(inside.sum())
    if n < 4:
        return None, {"status": "insufficient_registration_correspondences", "inliers": n}
    try:
        error = np.linalg.norm(project(A, a[inside]) - b[inside], axis=1)
        target = H @ np.linalg.inv(A)
        target /= target[2, 2]
        corners = np.array(
            [
                [region[0], region[1]],
                [region[2], region[1]],
                [region[2], region[3]],
                [region[0], region[3]],
            ],
            float,
        )
        warped = project(A, corners)
        area = float(cv2.contourArea(warped.astype(np.float32), oriented=True))
        rmse = float(np.sqrt(np.mean(error**2)))
        if (
            not np.isfinite(target).all()
            or area <= 0
        ):
            return None, {
                "status": "invalid_registration_geometry",
                "reason": "nonfinite_target_mapping" if not np.isfinite(target).all()
                          else "nonpositive_warped_panel_area",
                "matches": len(good), "inliers": n,
                "inlier_span_px": np.ptp(a[inside], axis=0).tolist(),
                "warped_area_px2": area if np.isfinite(area) else None,
                "rmse_px": rmse if np.isfinite(rmse) else None,
                "reference_to_current": A.tolist() if np.isfinite(A).all() else None,
                "physical_accuracy_validated": False,
            }
        edges = [
            e
            for r in RADII
            for e in ring_edges(
                current, target, r, region, angles=np.arange(1.5, 360, 12), search_px=3
            )
        ]
        rings = ring_summary(target, edges)
        return target, {
            "status": "image_registered_house_projection",
            "inliers": n,
            "matches": len(good),
            "rmse_px": rmse,
            "inlier_span_px": np.ptp(a[inside], axis=0).tolist(),
            "warped_area_px2": area,
            "quality_rejection_applied": False,
            "motion_model": model,
            "registration_method": "opencv_similarity_sift_ransac" if model == "similarity" else "opencv_lmeds_mutual_sift" if strategy == "adaptive_lmeds" else "baseline_sift_ransac",
            "estimator_assumption": "More than half of descriptor matches follow one camera motion; not independently verified" if strategy == "adaptive_lmeds" else "Preserved baseline fixed ratio/RANSAC tolerance; not empirically calibrated",
            "median_inlier_error_px": float(np.median(error)),
            "median_absolute_error_deviation_px": float(np.median(np.abs(error-np.median(error)))),
            "inlier_fraction": n / len(good),
            "parameter_source": "Full-panel default SIFT, mutual nearest matches, upstream LMEDS residual-based inliers; no application pixel tolerance" if strategy == "adaptive_lmeds" else "Frozen baseline estimator settings; adaptive candidate not promoted",

            "reference_to_current": A.tolist(),
            "partial_ring_check": rings,
            "metric_accuracy_validated": False,
        }
    except (ValueError, np.linalg.LinAlgError):
        return None, {"status": "singular_registration_geometry"}


def calibrate_sequence(frames, region, cut_times=(), max_anchor_age_s=None, initial=None):
    """Reuse shot-local anchors based on image registration, not a fixed age cutoff.

    max_anchor_age_s is an optional explicit caller budget; default is no age cap.
    Known cuts still prevent sharing geometry across shots.
    """
    result = {}
    accepted = []
    for t, frame in sorted(frames.items()):
        H, diag = initial[t] if initial and t in initial else calibrate_house(frame, region)
        result[t] = (H, diag)
        if H is not None:
            accepted.append(t)
    descriptors = {}

    def desc(t):
        if t not in descriptors:
            descriptors[t] = features(frames[t], region)
        return descriptors[t]

    for t, frame in sorted(frames.items()):
        if result[t][0] is not None:
            continue
        donors = [
            a
            for a in accepted
            if (max_anchor_age_s is None or abs(a - t) <= max_anchor_age_s)
            and not any(min(a, t) < c <= max(a, t) for c in cut_times)
        ]
        for a in sorted(donors, key=lambda a: abs(a - t)):
            H, diag = transfer(frames[a], frame, result[a][0], region, desc(a), desc(t))
            if H is not None:
                result[t] = (
                    H,
                    {
                        **diag,
                        "anchor_time_s": a,
                        "anchor_age_s": abs(a - t),
                        "anchor_geometry": result[a][1],
                    },
                )
                break
    return result
