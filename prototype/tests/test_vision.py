import unittest, sys, json
from pathlib import Path
import numpy as np
import cv2

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from vision_core import fit_calibration, project, ViewCalibrator, detect_caps, export_game_state


class GeometryAndEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = json.loads((ROOT / "vision/annotations/calibration.json").read_text())
        cls.cal = ViewCalibrator(cls.config["views"]["left"], ROOT / "vision/frames")

    def test_planar_roundtrip(self):
        H, _ = fit_calibration(self.config["views"]["left"])
        p = np.array([[320, 550], [500, 660], [600, 400]], float)
        np.testing.assert_allclose(project(np.linalg.inv(H), project(H, p)), p, atol=1e-7)

    def test_invalid_projection_rejected(self):
        H = np.eye(3)
        H[2, :] = 0
        with self.assertRaises(ValueError):
            project(H, [[1, 2]])

    def test_collinear_calibration_rejected(self):
        view = {"fit": [{"pixel": [i, i], "metres": [i, i]} for i in range(4)], "check": []}
        with self.assertRaises(ValueError):
            fit_calibration(view)

    def test_blank_image_causes_abstention(self):
        H, diagnostic = self.cal.register(np.zeros_like(self.cal.reference))
        self.assertIsNone(H)
        self.assertEqual(diagnostic["status"], "rejected")
        caps, d = detect_caps(np.zeros_like(self.cal.reference), H, self.cal.view)
        self.assertEqual(caps, [])
        self.assertEqual(d["status"], "abstained")

    def test_resolution_mismatch_rejected(self):
        H, d = self.cal.register(np.zeros((360, 640, 3), np.uint8))
        self.assertIsNone(H)
        self.assertIn("Resolution", d["reason"])

    def test_known_camera_translation_preserves_coordinates(self):
        A = np.array([[1.0, 0.0, 9.0], [0.0, 1.0, -6.0], [0.0, 0.0, 1.0]])
        frame = cv2.warpPerspective(self.cal.reference, A, (1920, 1080))
        H, d = self.cal.register(frame)
        self.assertIsNotNone(H, d)
        points = np.array([[479, 666], [335, 664], [481, 550]], float)
        np.testing.assert_allclose(
            project(H, project(A, points)), project(self.cal.H, points), atol=0.015
        )

    def test_reference_paint_is_not_a_new_stone(self):
        image = np.full((160, 160, 3), 240, np.uint8)
        cv2.rectangle(image, (75, 83), (85, 92), (130, 130, 130), -1)
        cv2.ellipse(image, (80, 80), (5, 3), 0, 0, 360, (0, 220, 240), -1)
        H = np.array([[0.02, 0, -1.6], [0, 0.02, -1.6], [0, 0, 1.0]])
        view = {"region": [0, 0, 160, 160], "world_bounds": [-2, -2, 2, 2]}
        caps, _ = detect_caps(image, H, view)
        self.assertEqual(len(caps), 1)
        suppressed, _ = detect_caps(image, H, view, image)
        self.assertEqual(suppressed, [])

    def test_experimental_projections_never_export_as_game_state(self):
        with self.assertRaises(ValueError):
            export_game_state(
                {
                    "completeness": "complete",
                    "calibration_status": "validated",
                    "candidates": [{"ice_plane_projection_m": [0, 0]}],
                }
            )


if __name__ == "__main__":
    unittest.main()
