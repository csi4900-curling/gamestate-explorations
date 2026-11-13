import unittest

from scripts.transfer_expanded_right_entry_full import associate_baseline


def entry(identifier, colour, time_s):
    return {
        "raw_track_id": identifier,
        "colour_claim": colour,
        "entry_crossing": {"time_s": time_s},
    }


class ExpandedRightEntryTransferTests(unittest.TestCase):
    def test_time_colour_pairing_preserves_both_unpaired_sides(self):
        result = associate_baseline(
            [entry("R1", "yellow", 10), entry("R2", "red", 20)],
            [entry("E1", "yellow", 11), entry("E2", "yellow", 20)],
        )
        self.assertEqual(
            result["time_colour_pairs"],
            [{"baseline_id": "R1", "expanded_id": "E1", "crossing_time_difference_s": 1}],
        )
        self.assertEqual(result["unpaired_baseline_ids"], ["R2"])
        self.assertEqual(result["unpaired_expanded_ids"], ["E2"])


if __name__ == "__main__":
    unittest.main()
