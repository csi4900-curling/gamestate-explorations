import unittest

from shot_motion_selection import selected_shot_indices


class ShotMotionSelectionTest(unittest.TestCase):
    def test_scans_unmatched_counter_window_and_following_shots(self):
        origins = [
            {
                "shot_id": f"S{i}",
                "interval_s": [i * 10, (i + 1) * 10],
                "probability": 0.05,
                "phase_supported": True,
            }
            for i in range(6)
        ]
        origins[0]["probability"] = 0.3
        decisions = [{"shot_id": row["shot_id"], "channel_support": []} for row in origins]
        decisions[0]["channel_support"] = [{"channel": "cap", "colour": "red"}]
        counters = [{"shot_id": None, "counter_update_s": 51}]
        fused = [{"shot_id": "S2", "counter_id": None}]
        self.assertEqual(
            selected_shot_indices(origins, counters, decisions, fused), [0, 1, 2, 3, 4, 5]
        )

    def test_rejects_misaligned_cap_decisions(self):
        with self.assertRaises(ValueError):
            selected_shot_indices([{"shot_id": "S1"}], [], [], [])


if __name__ == "__main__":
    unittest.main()
