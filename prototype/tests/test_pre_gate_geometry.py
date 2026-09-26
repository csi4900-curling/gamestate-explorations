import unittest, sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pre_gate_geometry import line_fit, audit_path


class PreGateTests(unittest.TestCase):
    def test_straight(self):
        t = np.arange(12)
        r = audit_path(np.c_[2 * t + 5, t])
        self.assertLess(r["endpoint_line"]["max_px"], 1e-10)
        self.assertLess(r["held_out_later_points"]["rms_px"], 1e-10)

    def test_curve(self):
        t = np.arange(12)
        r = audit_path(np.c_[0.2 * t * t, t])
        self.assertGreater(r["endpoint_line"]["max_px"], 1)
        self.assertGreater(r["held_out_later_points"]["rms_px"], 1)

    def test_projective_line_preserved(self):
        t = np.arange(12)
        p = np.c_[2 * t + 5, t, np.ones(12)]
        h = np.array([[1, 0.2, 3], [0.4, 2, 5], [0.01, 0.02, 1]])
        q = p @ h.T
        q = q[:, :2] / q[:, 2:]
        self.assertLess(line_fit(q)["max_px"], 1e-10)

    def test_short_not_predictive(self):
        self.assertIsNone(audit_path([[0, 0], [0, 1], [0.1, 2], [0, 3]])["held_out_later_points"])

    def test_invalid(self):
        for p in [[[0, 0]] * 3, [[0, 0], [1, 1], [float("nan"), 2]]]:
            with self.assertRaises(ValueError):
                line_fit(p)
