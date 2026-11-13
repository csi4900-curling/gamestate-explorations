import unittest

from right_backward_seam import backward_extension, choose_backward_point


def point(x, y, area=50):
    return {"pixel": [x, y], "cap_area_px2": area}


class RightBackwardSeamTests(unittest.TestCase):
    def test_unique_directional_chain_extends_only_to_observed_frames(self):
        frames = {11: [point(50, 125, 80)], 10: [point(48, 149, 100)]}
        first = {**point(52, 101), "time_s": 12.0}
        result = backward_extension(
            first, 9.5, "yellow", lambda time_s, colour: frames.get(time_s, [])
        )
        self.assertEqual(result["new_first_observed_s"], 10.0)
        self.assertEqual([x["time_s"] for x in result["added_observations"]], [10.0, 11.0])
        self.assertFalse(result["physical_identity_verified"])

    def test_ambiguous_or_wrong_direction_abstains(self):
        anchor = point(50, 100)
        self.assertEqual(
            choose_backward_point(anchor, [point(52, 90)])[1], "no_directional_colour_blob"
        )
        self.assertEqual(
            choose_backward_point(anchor, [point(50, 120), point(54, 125)])[1],
            "ambiguous_directional_blobs",
        )

    def test_large_area_change_abstains(self):
        self.assertEqual(
            choose_backward_point(point(50, 100, 50), [point(50, 120, 250)])[1],
            "no_directional_colour_blob",
        )


if __name__ == "__main__":
    unittest.main()
