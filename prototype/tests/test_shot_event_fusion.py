import unittest

from shot_event_fusion import fuse_shot_events


def origin(identifier, probability=0.001, predicted=0):
    return {
        "shot_id": identifier,
        "interval_s": [10, 20],
        "probability": probability,
        "predicted": predicted,
        "phase_supported": True,
    }


def decision(identifier, *, status="unconfirmed", colour=None, channels=()):
    return {
        "shot_id": identifier,
        "status": status,
        "reason": "test",
        "colour": colour,
        "colour_status": "unique" if colour else "ambiguous",
        "channel_support": [{"channel": c, "colour": colour or "red"} for c in channels],
    }


def counter(identifier, shot_id, colour):
    return {"counter_id": identifier, "shot_id": shot_id, "colour": colour}


class ShotEventFusionTest(unittest.TestCase):
    def test_counter_recovers_low_origin_with_explicit_provenance(self):
        result = fuse_shot_events(
            [origin("S01")], [decision("S01")], [counter("B01", "S01", "red")], allow_rescue=False
        )
        self.assertEqual(len(result["events"]), 1)
        event = result["events"][0]
        self.assertEqual(event["shot_id"], "S01")
        self.assertEqual(event["colour"], "red")
        self.assertEqual(event["evidence_sources"], ["delayed_counter_and_adjacent_motion"])

    def test_visual_candidate_survives_missing_counter(self):
        result = fuse_shot_events(
            [origin("S01", 0.9, 1)],
            [decision("S01", status="corroborated_candidate", colour="yellow")],
            [counter("B01", None, "red")],
            allow_rescue=False,
        )
        self.assertEqual(result["events"][0]["colour"], "yellow")
        self.assertEqual(result["unassociated_counter_events"][0]["counter_id"], "B01")

    def test_counter_colour_conflict_keeps_event_but_withholds_colour(self):
        result = fuse_shot_events(
            [origin("S01", 0.9, 1)],
            [decision("S01", status="corroborated_candidate", colour="yellow")],
            [counter("B01", "S01", "red")],
            allow_rescue=False,
        )
        self.assertEqual(result["events"][0]["status"], "candidate_with_colour_conflict")
        self.assertIsNone(result["events"][0]["colour"])
        self.assertEqual(result["conflicts"][0]["colour_status"], "conflict")

    def test_duplicate_counter_association_is_rejected(self):
        with self.assertRaises(ValueError):
            fuse_shot_events(
                [origin("S01")],
                [decision("S01")],
                [counter("B01", "S01", "red"), counter("B02", "S01", "red")],
                allow_rescue=False,
            )

    def test_following_only_counter_keeps_its_distinct_provenance(self):
        linked = counter("B01", "S01", "yellow")
        linked["association_route"] = "strong_origin_and_immediate_following_motion"
        result = fuse_shot_events(
            [origin("S01", 0.9, 1)], [decision("S01")], [linked], allow_rescue=False
        )
        self.assertEqual(
            result["events"][0]["evidence_sources"],
            ["delayed_counter_and_immediate_following_motion"],
        )

    def test_existing_visual_counter_link_preserves_colour_conflict(self):
        linked = counter("B01", "S01", "yellow")
        linked["association_route"] = "existing_visual_candidate_and_following_motion"
        result = fuse_shot_events(
            [origin("S01", 0.8, 1)],
            [decision("S01", status="corroborated_candidate", colour="red")],
            [linked],
            allow_rescue=False,
        )
        event = result["events"][0]
        self.assertEqual(event["colour_status"], "conflict")
        self.assertIn(
            "delayed_counter_linked_to_existing_visual_candidate", event["evidence_sources"]
        )


if __name__ == "__main__":
    unittest.main()
