import unittest

from counter_travel_fallback import travel_only_candidates


def motion(shot_id, colour, start, end):
    return {"shot_id": shot_id, "same_shot_candidates": [{
        "id": f"{shot_id}-{colour}", "colour": colour,
        "interval_s": [start, end]}]}


class CounterTravelFallbackTest(unittest.TestCase):
    def setUp(self):
        self.shots = [{"shot_id": "S1", "interval_s": [100, 120]}]
        self.counters = [{"counter_id": "B1", "colour": "yellow",
                          "counter_update_s": 110, "shot_id": None}]

    def test_dual_channel_travel_keeps_release_uncertain(self):
        rows = travel_only_candidates(self.counters, self.shots,
                                      [motion("S1", "yellow", 101, 108)],
                                      [motion("S1", "yellow", 102, 112)], [])
        self.assertEqual(rows[0]["status"], "unlocalized_travel_candidate")
        self.assertEqual(rows[0]["release_window_s"], [65, 101])
        self.assertEqual(rows[0]["observed_travel_window_s"], [101, 112])

    def test_wrong_colour_or_occupied_shot_abstains(self):
        cap = [motion("S1", "yellow", 101, 108)]
        learned = [motion("S1", "red", 102, 112)]
        self.assertEqual(travel_only_candidates(self.counters, self.shots,
                                               cap, learned, [])[0]["status"],
                         "abstained")
        learned = [motion("S1", "yellow", 102, 112)]
        self.assertEqual(travel_only_candidates(self.counters, self.shots,
                                               cap, learned, [{"shot_id": "S1"}])[0]
                         ["status"], "abstained")

    def test_motion_far_before_counter_does_not_match(self):
        cap = [motion("S1", "yellow", 101, 103)]
        learned = [motion("S1", "yellow", 102, 104)]
        self.assertEqual(travel_only_candidates(self.counters, self.shots,
                                               cap, learned, [])[0]["status"],
                         "abstained")

    def test_counter_update_before_receiving_view_track_keeps_release_broad(self):
        self.shots = [{"shot_id": "S1", "interval_s": [111, 130]}]
        cap = [motion("S1", "yellow", 112, 118)]
        learned = [motion("S1", "yellow", 112, 124)]
        row = travel_only_candidates(self.counters, self.shots,
                                     cap, learned, [])[0]
        self.assertEqual(row["status"], "unlocalized_travel_candidate")
        self.assertEqual(row["release_window_s"], [65, 110])
        self.assertEqual(row["observed_travel_window_s"], [112, 124])


if __name__ == "__main__":
    unittest.main()
