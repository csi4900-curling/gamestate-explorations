import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from broadcast_scoreboard import ScoreboardEvents


class ScoreboardStateTests(unittest.TestCase):
    def test_flicker_is_ignored_but_stable_single_decrement_is_emitted(self):
        tracker = ScoreboardEvents(stable_samples=3)
        for t in (0, 1, 2):
            tracker.update((8, 8), t)
        tracker.update((8, 7), 3)
        tracker.update(None, 4)
        for t in (5, 6, 7):
            tracker.update((8, 8), t)
        for t in (8, 9, 10):
            tracker.update((8, 7), t)
        self.assertEqual(len(tracker.events), 1)
        self.assertEqual(tracker.events[0]["colour"], "yellow")
        self.assertEqual(tracker.events[0]["evidence_interval_s"], [7, 8])
        self.assertEqual(tracker.events[0]["confirmed_at_s"], 10)

    def test_reset_and_multi_throw_gap_do_not_invent_event_times(self):
        tracker = ScoreboardEvents(stable_samples=2, max_gap_s=35)
        for t in (0, 1):
            tracker.update((5, 5), t)
        for t in (10, 11):
            tracker.update((3, 5), t)
        self.assertEqual(tracker.events, [])
        self.assertEqual(tracker.unresolved[0]["kind"], "multi_throw_or_long_graphic_gap")
        for t in (20, 21):
            tracker.update((8, 8), t)
        self.assertEqual(len(tracker.unresolved), 2)
        self.assertEqual(tracker.unresolved[1]["kind"], "counter_reset_or_inconsistent")
        self.assertEqual(tracker.events, [])

    def test_reset_blink_does_not_hide_first_throw_of_new_end(self):
        tracker = ScoreboardEvents(stable_samples=3)
        for t in (0, 1, 2):
            tracker.update((0, 1), t)
        tracker.update((8, 7), 10)
        tracker.update((8, 8), 11)
        for t, counts in ((12, (8, 7)), (13, (8, 8)), (14, (8, 7)), (15, (8, 8))):
            tracker.update(counts, t)
        for t in (16, 17, 18):
            tracker.update((8, 7), t)
        self.assertEqual(len(tracker.events), 1)
        self.assertEqual(tracker.events[0]["colour"], "yellow")
        self.assertEqual(tracker.events[0]["remaining_before"], (8, 8))

    def test_reset_grace_does_not_count_one_blinking_slot_twice(self):
        tracker = ScoreboardEvents(stable_samples=3)
        for t in (0, 1, 2):
            tracker.update((0, 0), t)
        tracker.update((8, 7), 10)
        tracker.update((8, 7), 11)
        tracker.update((8, 8), 12)
        for t in (13, 14, 15):
            tracker.update((8, 7), t)
        for t, counts in ((16, (8, 8)), (17, (8, 7)), (18, (8, 8)),
                          (19, (8, 7)), (20, (8, 8))):
            tracker.update(counts, t)
        for t in (21, 22, 23):
            tracker.update((8, 7), t)
        self.assertEqual(len(tracker.events), 1)
        self.assertEqual(tracker.events[0]["colour"], "yellow")

    def test_one_row_spurious_count_rise_is_not_an_end_reset(self):
        tracker = ScoreboardEvents(stable_samples=3)
        for t in (0, 1, 2):
            tracker.update((5, 5), t)
        tracker.update((8, 5), 3)
        for t in (4, 5, 6):
            tracker.update((5, 5), t)
        for t in (7, 8, 9):
            tracker.update((5, 4), t)
        self.assertEqual(len(tracker.events), 1)
        self.assertEqual(tracker.events[0]["colour"], "yellow")
        self.assertEqual(tracker.unresolved, [])

    def test_single_two_row_spurious_rise_cannot_reset_the_end(self):
        tracker = ScoreboardEvents(stable_samples=3)
        for t in (0, 1, 2):
            tracker.update((5, 6), t)
        tracker.update((8, 8), 3)
        for t in (4, 5, 6):
            tracker.update((5, 6), t)
        for t in (7, 8, 9):
            tracker.update((5, 5), t)
        self.assertEqual(tracker.unresolved, [])
        self.assertEqual(len(tracker.events), 1)
        self.assertEqual(tracker.events[0]["colour"], "yellow")
        self.assertEqual(tracker.events[0]["remaining_before"], (5, 6))

    def test_stable_one_row_rise_does_not_become_a_false_throw_on_return(self):
        tracker = ScoreboardEvents(stable_samples=3)
        for t in (0, 1, 2):
            tracker.update((6, 5), t)
        for t in (3, 4, 5, 6):
            tracker.update((7, 5), t)
        for t in (7, 8, 9):
            tracker.update((6, 5), t)
        self.assertEqual(tracker.events, [])
        self.assertEqual(len(tracker.unresolved), 1)
        self.assertEqual(tracker.unresolved[0]["kind"], "counter_reset_or_inconsistent")
        for t in (10, 11, 12):
            tracker.update((5, 5), t)
        self.assertEqual(len(tracker.events), 1)
        self.assertEqual(tracker.events[0]["remaining_before"], (6, 5))
        self.assertEqual(tracker.events[0]["remaining_after"], (5, 5))


if __name__ == "__main__":
    unittest.main()
