import copy
import unittest

from candidate_multiview_observation import build_observation_windows


class CandidateMultiviewObservationTests(unittest.TestCase):
    def setUp(self):
        self.sequence = {"source_sha256": "source", "candidate_sequence_count": 1,
                         "rows": [{"candidate_id": "R01-S01", "observation_kind": "left_tracked_crossing",
                                   "observation_time_s": 2.0, "colour_claim": "yellow",
                                   "right_entry": {"raw_track_id": "R002", "entry_time_s": 8.0},
                                   "sequence_proposal_id": "P001", "evidence_tier": "provisional",
                                   "crossing_source_class": None}]}
        self.left = {"source_sha256": "source", "tracks": [{"event_id": "S01",
                     "colour": "yellow", "crossing_time_s": 2.0,
                     "first_track_observation_s": 1.0, "last_track_observation_s": 4.0}]}
        self.right = {"source_sha256": "source", "entry_review_proposals": [{
            "raw_track_id": "R002", "colour_claim": "yellow",
            "entry_crossing": {"time_s": 8.0}, "observed_prefix_interval_s": [7.0, 9.0]}]}

    def test_two_view_seam_is_explicit_and_unverified(self):
        result = build_observation_windows(self.sequence, self.left, self.right)
        row = result["rows"][0]
        self.assertEqual(row["unobserved_camera_seam_s"], [4.0, 7.0])
        self.assertEqual(row["candidate_observation_envelope_s"], [1.0, 9.0])
        self.assertEqual(result["median_unobserved_camera_seam_s"], 3.0)
        self.assertFalse(row["physical_throw_segment_verified"])
        self.assertIsNone(row["physical_settle_time_s"])

    def test_overlapping_spans_are_rejected(self):
        right = copy.deepcopy(self.right)
        right["entry_review_proposals"][0]["observed_prefix_interval_s"] = [3.0, 9.0]
        with self.assertRaisesRegex(ValueError, "Overlapping camera spans"):
            build_observation_windows(self.sequence, self.left, right)

    def test_source_or_colour_disagreement_is_rejected(self):
        right = copy.deepcopy(self.right)
        right["source_sha256"] = "other"
        with self.assertRaisesRegex(ValueError, "source hashes disagree"):
            build_observation_windows(self.sequence, self.left, right)
        right = copy.deepcopy(self.right)
        right["entry_review_proposals"][0]["colour_claim"] = "red"
        with self.assertRaisesRegex(ValueError, "Right entry disagrees"):
            build_observation_windows(self.sequence, self.left, right)


if __name__ == "__main__":
    unittest.main()
