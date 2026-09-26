import sys, unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pipeline import panel_regions, sample_times, make_observation, require_simulation_ready


class ObservationContractTests(unittest.TestCase):
    def test_odd_width_panels_cover_frame_without_overlap(self):
        regions = panel_regions(641, 360, "dual_end")
        self.assertEqual(regions, [("left", 0, 0, 320, 360), ("right", 320, 0, 641, 360)])

    def test_sampling_never_requests_past_end(self):
        self.assertEqual(sample_times(25, 10), [0.0, 10.0, 20.0])
        self.assertEqual(sample_times(0.5, 10), [0.0])

    def test_reject_bad_sampling(self):
        for duration, interval in [(0, 10), (float("nan"), 10), (20, 0), (20, float("inf"))]:
            with self.assertRaises(ValueError):
                sample_times(duration, interval)

    def test_useful_view_is_not_a_validated_game_state(self):
        observation = make_observation("left", 20, "frame.jpg", (0, 0, 320, 360), {})
        self.assertEqual(observation["completeness"], "unknown")
        observation["review_status"] = "useful_view"
        with self.assertRaises(ValueError):
            require_simulation_ready(observation)

    def test_status_labels_alone_cannot_enable_export(self):
        observation = {
            "calibration_status": "validated",
            "completeness": "complete",
            "review_status": "validated",
        }
        with self.assertRaises(ValueError):
            require_simulation_ready(observation)

    def test_unknown_profile_fails_instead_of_silent_guess(self):
        with self.assertRaises(ValueError):
            panel_regions(640, 360, "four_panels")


if __name__ == "__main__":
    unittest.main()
