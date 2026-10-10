import unittest

from prototype.counter_shot_alignment import (
    align_counter_events,
    link_existing_visual_candidates,
    rescue_following_only,
)


def shot(identifier, start, end, probability, *, phase=True):
    return {
        "shot_id": identifier,
        "interval_s": [start, end],
        "probability": probability,
        "phase_supported": phase,
    }


def motion(identifier, colour=None):
    candidates = [{"colour": colour}] if colour else []
    return {
        "shot_id": identifier,
        "same_shot_candidates": candidates,
        "following_shot_candidates": candidates,
    }


def event(identifier, colour, start, update):
    return {
        "id": identifier,
        "colour": colour,
        "evidence_interval_s": [start, update],
        "crossing_time_s": update,
    }


class CounterShotAlignmentTest(unittest.TestCase):
    def test_delayed_update_recovers_low_probability_delivery(self):
        shots = [
            shot("preparation", 20, 24, 0.00005),
            shot("delivery", 24, 40, 0.0027),
            shot("travel", 40, 60, 0.00095),
        ]
        rows = align_counter_events(
            shots,
            [event("B01", "red", 36, 52)],
            {"cap": [motion(s["shot_id"], "red") for s in shots]},
        )
        self.assertEqual(rows[0]["shot_id"], "delivery")

    def test_narrow_counter_change_can_lag_delivery_by_thirty_seconds(self):
        shots = [shot("delivery", 10, 20, 0.8), shot("travel", 20, 35, 0.01)]
        rows = align_counter_events(
            shots,
            [event("B01", "yellow", 49, 50)],
            {"cap": [motion("delivery", "yellow"), motion("travel")]},
        )
        self.assertEqual(rows[0]["shot_id"], "delivery")

    def test_abstains_when_motion_candidates_are_too_close(self):
        shots = [shot("A", 10, 20, 0.4), shot("B", 20, 30, 0.3)]
        rows = align_counter_events(
            shots,
            [event("B01", "yellow", 25, 35)],
            {"cap": [motion("A", "yellow"), motion("B", "yellow")]},
        )
        self.assertEqual(rows[0]["status"], "abstained")
        self.assertIsNone(rows[0]["shot_id"])

    def test_requires_same_colour_motion_and_live_phase(self):
        shots = [
            shot("replay", 10, 20, 0.99, phase=False),
            shot("other_colour", 20, 30, 0.8),
            shot("delivery", 30, 40, 0.1),
        ]
        rows = align_counter_events(
            shots,
            [event("B01", "red", 32, 45)],
            {
                "cap": [
                    motion("replay", "red"),
                    motion("other_colour", "yellow"),
                    motion("delivery", "red"),
                ]
            },
        )
        self.assertEqual(rows[0]["shot_id"], "delivery")

    def test_zero_scores_do_not_break_an_ambiguous_tie(self):
        shots = [shot("A", 10, 20, 0), shot("B", 20, 30, 0)]
        rows = align_counter_events(
            shots, [event("B01", "red", 25, 35)], {"cap": [motion("A", "red"), motion("B", "red")]}
        )
        self.assertEqual(rows[0]["status"], "abstained")

    def test_immediate_following_motion_rescues_short_delivery_shot(self):
        shots = [shot("delivery", 10, 14, 0.9), shot("travel", 14, 30, 0.01)]
        audits = {
            name: [
                {
                    "shot_id": "delivery",
                    "following_shot_candidates": [{"colour": "yellow", "interval_s": [14.2, 20]}],
                },
                {"shot_id": "travel", "following_shot_candidates": []},
            ]
            for name in ("cap", "learned")
        }
        initial = [
            {
                "counter_id": "B01",
                "colour": "yellow",
                "counter_update_s": 35,
                "shot_id": None,
                "status": "abstained",
            }
        ]
        result = rescue_following_only(initial, shots, audits)
        self.assertEqual(result[0]["shot_id"], "delivery")
        self.assertEqual(
            result[0]["association_route"], "strong_origin_and_immediate_following_motion"
        )

    def test_following_motion_must_start_near_cut_in_both_channels(self):
        shots = [shot("delivery", 10, 14, 0.9)]
        audits = {
            "cap": [
                {
                    "shot_id": "delivery",
                    "following_shot_candidates": [{"colour": "yellow", "interval_s": [14.1, 20]}],
                }
            ],
            "learned": [
                {
                    "shot_id": "delivery",
                    "following_shot_candidates": [{"colour": "yellow", "interval_s": [17, 21]}],
                }
            ],
        }
        initial = [
            {
                "counter_id": "B01",
                "colour": "yellow",
                "counter_update_s": 35,
                "shot_id": None,
                "status": "abstained",
            }
        ]
        self.assertIsNone(rescue_following_only(initial, shots, audits)[0]["shot_id"])

    def test_existing_visual_candidate_takes_counter_without_new_event(self):
        shots = [shot("S1", 10, 14, 0.4), shot("S2", 14, 30, 0.01)]
        audits = {
            name: [
                {
                    "shot_id": "S1",
                    "following_shot_candidates": [{"colour": "yellow", "interval_s": [14, 23]}],
                },
                {"shot_id": "S2", "following_shot_candidates": []},
            ]
            for name in ("cap", "learned")
        }
        initial = [
            {
                "counter_id": "B01",
                "colour": "yellow",
                "counter_update_s": 25,
                "shot_id": None,
                "status": "abstained",
            }
        ]
        existing = [{"shot_id": "S1", "counter_id": None, "colour": "red"}]
        result = link_existing_visual_candidates(initial, shots, existing, audits)
        self.assertEqual(result[0]["shot_id"], "S1")
        self.assertEqual(
            result[0]["association_route"], "existing_visual_candidate_and_following_motion"
        )

    def test_existing_visual_link_abstains_if_two_candidates_fit(self):
        shots = [shot("S1", 10, 14, 0.4), shot("S2", 14, 20, 0.5), shot("S3", 20, 30, 0.01)]
        audits = {
            name: [
                {
                    "shot_id": row["shot_id"],
                    "following_shot_candidates": [
                        {
                            "colour": "yellow",
                            "interval_s": [row["interval_s"][1], row["interval_s"][1] + 5],
                        }
                    ],
                }
                for row in shots
            ]
            for name in ("cap", "learned")
        }
        initial = [
            {
                "counter_id": "B01",
                "colour": "yellow",
                "counter_update_s": 25,
                "shot_id": None,
                "status": "abstained",
            }
        ]
        existing = [{"shot_id": sid, "counter_id": None} for sid in ("S1", "S2")]
        result = link_existing_visual_candidates(initial, shots, existing, audits)
        self.assertIsNone(result[0]["shot_id"])


if __name__ == "__main__":
    unittest.main()
