from pathlib import Path
import sys, unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from prototype.rink_coordinates import (
    TEE_DISTANCE_M,
    handoff_from_rink,
    handoff_geometry,
    rink_position,
)

HOG = {"left": -6.401, "right": 6.401}


class RinkCoordinateTests(unittest.TestCase):
    def test_left_departure(self):
        self.assertEqual(rink_position([1, -8], panel="left", role="departure", hog_y_m=HOG), [1, 8])

    def test_right_departure(self):
        self.assertEqual(rink_position([-1, 15], panel="right", role="departure", hog_y_m=HOG), [-1, 15])

    def test_right_receiving(self):
        y = rink_position([-1.33, 15.09], panel="right", role="receiving", hog_y_m=HOG)[1]
        self.assertAlmostEqual(y, TEE_DISTANCE_M - 15.09, places=6)

    def test_left_receiving_end_two_regression(self):
        # End 2 reverses the camera roles. The old view-only transform returned
        # 51.6 m for this point and produced a 66 m handoff gap; the panel-aware
        # transform must return 17.85 m.
        y = rink_position([-1.9, -16.9], panel="left", role="receiving", hog_y_m=HOG)[1]
        self.assertAlmostEqual(y, TEE_DISTANCE_M - 16.9, places=6)
        self.assertLess(y, TEE_DISTANCE_M)
        self.assertGreater(y, 0)

    def test_lateral_sign_recorded(self):
        self.assertEqual(rink_position([0.7, -8], panel="left", role="departure",
                                       hog_y_m=HOG, lateral_sign=-1)[0], -0.7)

    def test_end_two_handoff_is_plausible(self):
        result = handoff_geometry(
            [0.1, 15.0], departure_panel="right",
            receiving_local=[-1.9, -16.9], receiving_panel="left",
            departure_time_s=930.6, receiving_time_s=931.1, hog_y_m=HOG,
        )
        self.assertEqual(result["spatial_consistency"], "consistent")
        self.assertEqual(result["gap_status"], "plausible_gap")
        self.assertEqual(result["speed_status"], "plausible_speed")
        self.assertLess(result["gap_m"], 5.0)
        self.assertLess(result["implied_speed_m_s"], 10.0)
        self.assertFalse(result["physical_identity_verified"])

    def test_impossible_handoff_is_flagged(self):
        result = handoff_geometry(
            [0.1, 15.0], departure_panel="right",
            receiving_local=[-1.9, -16.9], receiving_panel="left",
            departure_time_s=100.0, receiving_time_s=100.1, hog_y_m=HOG,
        )
        self.assertEqual(result["spatial_consistency"], "high_speed")
        self.assertEqual(result["speed_status"], "high_speed")
        self.assertEqual(result["gap_status"], "plausible_gap")
        self.assertGreater(result["implied_speed_m_s"], 10.0)

    def test_implausible_gap(self):
        result = handoff_from_rink([0.0, 16.0], [0.0, 82.0],
                                   departure_time_s=100.0,
                                   receiving_time_s=100.4)
        self.assertEqual(result["gap_status"], "implausible_gap")
        self.assertEqual(result["spatial_consistency"], "implausible_gap")
        self.assertGreater(result["gap_m"], 30.0)

    def test_missing_time(self):
        result = handoff_geometry(
            [0, 1], departure_panel="right", receiving_local=[0, 2],
            receiving_panel="left", departure_time_s=10, receiving_time_s=10,
            hog_y_m=HOG,
        )
        self.assertEqual(result["spatial_consistency"], "missing_or_nonpositive_time")

    def test_rejects_unknown_panel_role_and_bad_hog(self):
        with self.assertRaises(ValueError):
            rink_position([0, 0], panel="middle", role="departure", hog_y_m=HOG)
        with self.assertRaises(ValueError):
            rink_position([0, 0], panel="left", role="unknown", hog_y_m=HOG)
        with self.assertRaises(ValueError):
            rink_position([0, 0], panel="left", role="departure", hog_y_m={"left": 0, "right": 1})
        with self.assertRaises(ValueError):
            rink_position([float("nan"), 0], panel="left", role="departure", hog_y_m=HOG)


if __name__ == "__main__":
    unittest.main()
