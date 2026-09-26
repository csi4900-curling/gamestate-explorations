"""Numerical checks for the failure modes found in this experiment."""

import unittest
import numpy as np
from geometry import project, fit, world


class CalibrationChecks(unittest.TestCase):
    def test_known_projective_transform_on_unseen_points(self):
        # Known generating camera; fit on six landmarks, verify different points.
        camera = np.array([[170, 12, 480], [5, 130, 270], [0.025, -0.04, 1.0]])
        metric = np.array([[-1.8, 0], [1.8, 0], [0, -1.8], [0, 1.8], [-1, 1], [1, -1]])
        pixel = project(camera, metric)
        H = fit(pixel, metric)
        unseen = np.array([[0.31, 0.87], [-0.65, -0.29], [1.5, 1.1]])
        np.testing.assert_allclose(project(H, project(camera, unseen)), unseen, atol=1e-5)

    def test_many_collinear_landmarks_plus_one_are_rejected(self):
        metric = np.array([world(k) for k in ["oL", "oR", "oT", "rL", "rR", "wL", "wR"]])
        pixel = metric * 100 + [480, 270]
        with self.assertRaisesRegex(ValueError, "unidentifiable"):
            fit(pixel, metric)
        affine = fit(pixel, metric, "affine")
        np.testing.assert_allclose(project(affine, [[480, 370]]), [[0, 1]], atol=1e-9)

    def test_image_resize_preserves_world_coordinates(self):
        w = np.array([[-1, -1], [1, -1], [1, 1], [-1, 1], [0, 0.0]])
        p = w * [100, 120] + [480, 270]
        h = fit(p, w)
        h2 = fit(p * 2, w)
        np.testing.assert_allclose(project(h, [[500, 290]]), project(h2, [[1000, 580]]), atol=1e-6)

    def test_affine_rejects_line_only(self):
        with self.assertRaisesRegex(ValueError, "degenerate"):
            fit([[1, 1], [2, 2], [3, 3]], [[0, 0], [1, 1], [2, 2]], "affine")


if __name__ == "__main__":
    unittest.main()
