import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from two_stage_throw_triage import triage_candidates


def event(event_id, time):
    return {"id": event_id, "crossing_time_s": time, "colour": "red"}


class TwoStageTriageTests(unittest.TestCase):
    def test_preserves_every_proposal_and_withheld_reason(self):
        a, b, c = event("A", 1), event("B", 2), event("C", 3)
        corridor = {
            "events": [a, b],
            "withheld_events": [c],
            "screened_events": [
                {"id": "A", "status": "ice_corridor_candidate"},
                {"id": "B", "status": "ice_corridor_candidate"},
                {"id": "C", "status": "off_corridor_unconfirmed"},
            ],
        }
        motion = {
            "events": [a],
            "withheld_events": [b],
            "decisions": [
                {"id": "A", "reason": "motion_supported"},
                {"id": "B", "reason": "below_layout_motion_speed"},
            ],
        }
        result = triage_candidates([a, b, c], [("corridor", corridor), ("motion", motion)])
        self.assertEqual(
            result["counts"],
            {
                "proposed": 3,
                "auto_confirmed": 1,
                "needs_review": 2,
            },
        )
        self.assertEqual([x["id"] for x in result["review_events"]], ["B", "C"])
        self.assertEqual(
            result["proposals"][1]["stage_evidence"][-1]["reason"], "below_layout_motion_speed"
        )
        self.assertIsNone(result["proposals"][2]["release_time_s"])

    def test_rejects_a_stage_that_drops_evidence(self):
        a, b = event("A", 1), event("B", 2)
        with self.assertRaises(ValueError):
            triage_candidates([a, b], [("bad", {"events": [a], "withheld_events": []})])

    def test_requires_unique_ids_and_stages(self):
        a = event("A", 1)
        stage = {"events": [a], "withheld_events": []}
        with self.assertRaises(ValueError):
            triage_candidates([a, a], [("one", stage)])
        with self.assertRaises(ValueError):
            triage_candidates([a], [("one", stage), ("one", stage)])


if __name__ == "__main__":
    unittest.main()
