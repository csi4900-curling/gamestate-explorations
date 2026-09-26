import unittest, sys, json
from pathlib import Path
import cv2, numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from rectification_core import (
    canvas_transform,
    rectify,
    refine_calibration,
    validate_rings,
    VideoRectifier,
)
from vision_core import project


class RectificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.view = json.loads((ROOT / "vision/annotations/calibration.json").read_text())["views"][
            "left"
        ]
        cls.image = cv2.imread(str(ROOT / "vision/frames" / cls.view["reference_frame"]))
        cls.H, cls.report = refine_calibration(cls.image, cls.view)

    def test_metric_canvas_has_equal_axis_scale(self):
        C, size = canvas_transform()
        p = project(C, [[0, 0], [1, 0], [0, 1]])
        self.assertAlmostEqual(np.linalg.norm(p[1] - p[0]), np.linalg.norm(p[2] - p[0]))
        self.assertEqual(size, (588, 588))

    def test_inner_ring_excluded_from_fit(self):
        self.assertTrue(all(e["radius_m"] > 0.7 for e in self.report["fit_observations"]))
        fit = {tuple(e["pixel"]) for e in self.report["fit_observations"]}
        hold = {tuple(e["pixel"]) for e in self.report["heldout_observations"]}
        self.assertFalse(fit & hold)

    def test_blank_ice_does_not_pass_ring_gate(self):
        passed, _ = validate_rings(np.full_like(self.image, 180), self.H, self.view["region"])
        self.assertFalse(passed)

    def test_bad_geometry_does_not_pass_ring_gate(self):
        A = np.array([[1, 0, 30], [0, 1, 30], [0, 0, 1.0]])
        passed, _ = validate_rings(self.image, self.H @ np.linalg.inv(A), self.view["region"])
        self.assertFalse(passed)

    def test_reference_ring_geometry_supported(self):
        passed, quality = validate_rings(self.image, self.H, self.view["region"])
        self.assertTrue(passed, quality)

    def test_other_panel_pixels_cannot_leak_into_rectification(self):
        changed = self.image.copy()
        changed[:, 960:] = (0, 0, 255)
        a, mask = rectify(self.image, self.H, self.view["region"])
        b, _ = rectify(changed, self.H, self.view["region"])
        np.testing.assert_array_equal(a, b)
        self.assertEqual(mask.shape, (588, 588))

    def test_unavailable_transform_not_rendered(self):
        with self.assertRaises(ValueError):
            rectify(self.image, None, self.view["region"])

    def test_camera_motion_compensation_and_cut_abstention(self):
        rectifier = VideoRectifier(self.view, ROOT / "vision/frames", self.H)
        _, q = rectifier.step(self.image, 0)
        self.assertEqual(q["status"], "supported")
        # Known subpixel motion between absolute anchors exercises actual optical flow.
        A = np.array([[1.0, 0.0, 1.5], [0.0, 1.0, -0.7], [0.0, 0.0, 1.0]])
        moved = cv2.warpPerspective(self.image, A, (1920, 1080))
        H, q = rectifier.step(moved, 1 / 30)
        self.assertIsNotNone(H, q)
        self.assertEqual(q["method"], "optical_flow")
        pts = np.array([[335, 664], [481, 550], [622, 670], [477, 709]], float)
        np.testing.assert_allclose(project(H, project(A, pts)), project(self.H, pts), atol=0.015)
        H, q = rectifier.step(np.zeros_like(self.image), 2 / 30)
        self.assertIsNone(H)
        self.assertEqual(q["status"], "unavailable")

    def test_absolute_registration_handles_known_zoom_and_translation(self):
        rectifier = VideoRectifier(self.view, ROOT / "vision/frames", self.H)
        A = np.array([[1.025, 0.002, -7.0], [-0.001, 1.025, -9.0], [0.000003, 0, 1.0]])
        moved = cv2.warpPerspective(self.image, A, (1920, 1080))
        H, q = rectifier.step(moved, 0)
        self.assertIsNotNone(H, q)
        pts = np.array([[335, 664], [481, 550], [622, 670], [477, 709]], float)
        np.testing.assert_allclose(project(H, project(A, pts)), project(self.H, pts), atol=0.025)


if __name__ == "__main__":
    unittest.main()
