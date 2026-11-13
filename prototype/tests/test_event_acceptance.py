import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from event_acceptance import assess_recording


class EventAcceptanceTests(unittest.TestCase):
    measured = {"measured_source_sha256": "abc", "measured_source_duration_s": 60.0}

    def fixture(self):
        source = "abc"
        prediction = {
            "source_sha256": source,
            "source_interval_s": [0, 60],
            "source_duration_s": 60,
            "coverage_gaps_s": [],
            "coverage_verified": True,
            "events": [{"id": "P1", "colour": "red", "crossing_time_s": 10}],
        }
        reference = {
            "source_sha256": source,
            "source_interval_s": [0, 60],
            "source_duration_s": 60,
            "source_duration_verified": True,
            "exhaustive": True,
            "reference_method": "human_independent",
            "events": [{"id": "R1", "colour": "red", "delivery_interval_s": [9, 11]}],
        }
        return prediction, reference

    def test_complete_independent_recording_can_pass(self):
        prediction, reference = self.fixture()
        self.assertEqual(
            assess_recording(prediction, reference, **self.measured)["reason"], "target_met"
        )

    def test_missing_or_different_source_file_cannot_pass(self):
        prediction, reference = self.fixture()
        self.assertEqual(
            assess_recording(prediction, reference)["reason"], "unverified_source_video_fingerprint"
        )
        self.assertEqual(
            assess_recording(
                prediction,
                reference,
                measured_source_sha256="different",
                measured_source_duration_s=60,
            )["reason"],
            "unverified_source_video_fingerprint",
        )

    def test_declared_excerpt_duration_cannot_stand_in_for_full_video(self):
        prediction, reference = self.fixture()
        self.assertEqual(
            assess_recording(
                prediction, reference, measured_source_sha256="abc", measured_source_duration_s=120
            )["reason"],
            "unverified_full_recording_scope",
        )

    def test_partial_timeline_cannot_pass_even_if_observed_event_matches(self):
        prediction, reference = self.fixture()
        prediction["coverage_gaps_s"] = [[30, 40]]
        prediction["observed_events"] = prediction.pop("events")
        result = assess_recording(prediction, reference, **self.measured)
        self.assertEqual(result["reason"], "incomplete_coverage")
        self.assertIsNone(result["score"])

    def test_matching_partial_intervals_cannot_claim_full_recording(self):
        prediction, reference = self.fixture()
        prediction["source_duration_s"] = 120
        reference["source_duration_s"] = 120
        result = assess_recording(prediction, reference, **self.measured)
        self.assertEqual(result["reason"], "unverified_full_recording_scope")
        self.assertIsNone(result["score"])

    def test_unverified_source_duration_cannot_pass(self):
        prediction, reference = self.fixture()
        reference["source_duration_verified"] = False
        self.assertEqual(
            assess_recording(prediction, reference, **self.measured)["reason"],
            "unverified_full_recording_scope",
        )

    def test_agent_reference_scores_but_cannot_validate(self):
        prediction, reference = self.fixture()
        reference["reference_method"] = "agent_blind"
        result = assess_recording(prediction, reference, **self.measured)
        self.assertEqual(result["reason"], "non_independent_reference")
        self.assertEqual(result["score"]["f1"], 1)

    def test_both_precision_and_recall_must_clear_target(self):
        prediction, reference = self.fixture()
        prediction["events"].append({"id": "P2", "colour": "yellow", "crossing_time_s": 30})
        self.assertEqual(
            assess_recording(prediction, reference, **self.measured)["reason"],
            "below_precision_or_recall_target",
        )
        prediction["events"].pop()
        reference["events"].append(
            {"id": "R2", "colour": "yellow", "delivery_interval_s": [29, 31]}
        )
        self.assertEqual(
            assess_recording(prediction, reference, **self.measured)["reason"],
            "below_precision_or_recall_target",
        )


if __name__ == "__main__":
    unittest.main()
