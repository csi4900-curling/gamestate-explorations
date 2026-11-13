import unittest, sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from body_localization import (
    conditional_camera,
    height_correct,
    detect_and_localize,
    localize,
    transported_reference_camera,
)
from vision_core import project


class BodyLocalizationTests(unittest.TestCase):
    def camera_fixture(self):
        # X right, Y foreground, Z up: consistent with view-local coordinates in the model.
        C = np.array([0.0, 12.0, 5.0])
        e = 5 / 13
        c = 12 / 13
        R = np.array([[1, 0, 0], [0, e, -c], [0, -c, -e]], float)
        t = -R @ C
        K = np.array([[1800.0, 0, 960], [0, 1800.0, 540], [0, 0, 1.0]])
        P = K @ np.column_stack([R, t])
        M = P[:, [0, 1, 3]]
        return np.linalg.inv(M), P, C

    def test_known_height_projection_recovers_ground_location(self):
        H, P, C = self.camera_fixture()
        camera, diag = conditional_camera(H, [0, 0, 1920, 1080])
        self.assertIsNotNone(camera, diag)
        np.testing.assert_allclose(diag["camera_centre_m"], C, atol=1e-8)
        for xy in [[-0.6, -1.2], [0, 0], [1, 1.5]]:
            xyz = np.array([*xy, 0.136, 1.0])
            px = P @ xyz
            px = px[:2] / px[2]
            corrected = height_correct(camera, px, 0.136)
            np.testing.assert_allclose(corrected, xy, atol=1e-8)
            self.assertGreater(np.linalg.norm(project(H, [px])[0] - xy), 0.25)

    def test_reference_camera_transport_preserves_known_ground_point(self):
        H, P, _ = self.camera_fixture()
        A = np.array([[1.02, 0.001, 8.0], [0, 1.02, -3.0], [0, 0, 1.0]])
        current_H = H @ np.linalg.inv(A)
        prior = transported_reference_camera(H, current_H, [0, 0, 1920, 1080])
        q = P @ np.array([0.5, -0.3, 0.136, 1.0])
        pixel = project(A, [q[:2] / q[2]])[0]
        xy, diag = localize(current_H, pixel, [0, 0, 1920, 1080], "cap_with_body_support", prior)
        np.testing.assert_allclose(xy, [0.5, -0.3], atol=1e-8)
        self.assertIn("temporal_model", diag["camera"])

    def test_zero_height_is_original_plane_projection(self):
        H, _, _ = self.camera_fixture()
        camera, _ = conditional_camera(H, [0, 0, 1920, 1080])
        pixel = [900, 600]
        np.testing.assert_allclose(
            height_correct(camera, pixel, 0), project(H, [pixel])[0], atol=1e-9
        )

    def test_frontoparallel_pose_is_not_invented(self):
        H = np.array([[0.005, 0, -1.0], [0, 0.005, -1.0], [0, 0, 1.0]])
        camera, diag = conditional_camera(H, [0, 0, 400, 400])
        self.assertIsNone(camera)
        self.assertEqual(diag["status"], "unidentifiable")
        xy, meta = localize(H, [200, 200], [0, 0, 400, 400], "body_outline")
        np.testing.assert_allclose(xy, [0, 0])
        self.assertEqual(meta["status"], "near_overhead_body_approximation")

    def test_ambiguous_low_angle_affine_camera_abstains(self):
        H = np.array([[0.005, 0, -1.0], [0, 0.05, -10.0], [0, 0, 1.0]])
        xy, meta = localize(H, [200, 200], [0, 0, 400, 400], "cap_with_body_support")
        self.assertIsNone(xy)
        self.assertEqual(meta["status"], "unavailable")

    def test_blank_frame_emits_no_body_detections(self):
        im = np.full((400, 400, 3), 230, np.uint8)
        H = np.array([[0.005, 0, -1.0], [0, 0.005, -1.0], [0, 0, 1.0]])
        p, _ = detect_and_localize(
            im, H, {"region": [0, 0, 400, 400], "world_bounds": [-2, -2, 2, 2]}
        )
        self.assertEqual(p, [])

    def test_missing_calibration_never_outputs_position(self):
        p, d = detect_and_localize(np.zeros((100, 100, 3), np.uint8), None, {})
        self.assertEqual(p, [])
        self.assertEqual(d["status"], "unavailable")

    def test_height_sensitivity_is_exposed(self):
        H, P, _ = self.camera_fixture()
        p = P @ np.array([0.0, 0.0, 0.136, 1.0])
        p = p[:2] / p[2]
        xy, meta = localize(H, p, [0, 0, 1920, 1080], "cap_with_body_support")
        np.testing.assert_allclose(xy, [0, 0], atol=1e-8)
        self.assertGreater(meta["height_intrinsics_sensitivity_m"], 0.04)


if __name__ == "__main__":
    unittest.main()


def test_finite_inconsistent_camera_is_returned_with_residual():
    # Deliberately violate the assumed zero skew; residual is diagnostic, not a gate.
    C = np.array([0.,12.,5.])
    R = np.array([[1,0,0],[0,5/13,-12/13],[0,-12/13,-5/13]])
    K = np.array([[600.,120.,480],[0,600.,180],[0,0,1.]])
    P = K @ np.column_stack([R,-R@C])
    H = np.linalg.inv(P[:,[0,1,3]])
    camera, diagnostic = conditional_camera(H, [320,0,640,360])
    assert camera is not None, diagnostic
    assert diagnostic['orthogonality_residual'] > .06
    assert diagnostic['quality_rejection_applied'] is False
    assert np.isfinite(height_correct(camera,[480,180],.136)).all()
