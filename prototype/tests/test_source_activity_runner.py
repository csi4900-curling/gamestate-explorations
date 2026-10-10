"""The routed runner must attach and verify detector-blind coverage evidence."""

import json
from pathlib import Path
import sys
import tempfile
import unittest

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cache_contract import file_sha256
from scripts.run_throw_pipeline import (attach_source_activity, attach_right_view_review,
                                        attach_camera_aware_fusion,
                                        attach_candidate_review_union,
                                        attach_right_partial_boards,
                                        attach_candidate_state_handoff,
                                        attach_right_board_sequence,
                                        attach_left_candidate_boards,
                                        attach_candidate_state_handoff_v2,
                                        attach_candidate_image_board_sequence,
                                        attach_candidate_house_ellipse)
from scripts.audit_split_panel_freeze import normalized_split_frame


class SourceActivityRunnerTests(unittest.TestCase):
    def test_split_frame_normalization_handles_hd(self):
        frame = np.full((720, 1280, 3), 127, dtype=np.uint8)
        self.assertEqual(normalized_split_frame(frame).shape, (360, 640, 3))
        with self.assertRaisesRegex(ValueError, "16:9"):
            normalized_split_frame(frame[:, :1000])

    def test_full_activity_sidecar_marks_static_left_and_resume_checks_hashes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            video = root / "source.avi"
            writer = cv2.VideoWriter(str(video), cv2.VideoWriter_fourcc(*"MJPG"),
                                     1, (640, 360))
            self.assertTrue(writer.isOpened())
            for second in range(70):
                frame = np.full((360, 640, 3), 180, dtype=np.uint8)
                frame[:, 320:] = 0 if second // 5 % 2 else 255
                if 10 <= second <= 13:
                    y = 285 - (second - 10) * 24
                    cv2.rectangle(frame, (395, y), (409, y + 8), (0, 0, 255), -1)
                writer.write(frame)
            writer.release()
            timeline_path = root / "timeline.json"
            timeline = {
                "source_id": "synthetic", "source_sha256": file_sha256(video),
                "source_interval_s": [0, 70],
                "supported_runs": [{"id": "R01", "layout": "split_2024",
                                    "interval_s": [0, 70],
                                    "adapter_artifact": "run-01/events.json"}],
                "coverage_gaps_s": [], "observed_events": [],
            }
            run_dir = root / "run-01"
            run_dir.mkdir()
            event_path = run_dir / "events.json"
            event_path.write_text(json.dumps({"events": []}) + "\n")
            raw_path = run_dir / "raw.json"
            raw_path.write_text(json.dumps({
                "source_sha256": timeline["source_sha256"],
                "source_interval_s": [0, 70], "events": [],
            }) + "\n")
            (run_dir / "triage.json").write_text(json.dumps({
                "source_sha256": timeline["source_sha256"],
                "source_interval_s": [0, 70],
                "confirmation_sha256": file_sha256(event_path),
                "raw_sha256": file_sha256(raw_path),
                "proposals": [],
            }) + "\n")
            timeline_path.write_text(json.dumps(timeline) + "\n")
            first = attach_source_activity(video, timeline["source_sha256"],
                                           [0, 70], root, timeline_path)
            self.assertEqual(first["newly_unsupported_seconds"], 65)
            self.assertEqual(first["original_event_count_unchanged"], 0)
            self.assertEqual(attach_source_activity(video, timeline["source_sha256"],
                                                    [0, 70], root, timeline_path), first)
            review = attach_right_view_review(video, timeline["source_sha256"], root)
            raw = json.loads((root / "right-motion-in-blind.json").read_text())
            self.assertGreaterEqual(sum(r["entry_review_count"] for r in review["intervals"]), 1,
                                    msg=json.dumps(raw["intervals"][0]["tracks"]))
            self.assertEqual(attach_right_view_review(video, timeline["source_sha256"], root),
                             review)
            fusion = attach_camera_aware_fusion(root, timeline["source_sha256"], timeline_path)
            self.assertEqual(fusion["fusion_status_counts"],
                             {"right_only_left_static_review": 1})
            self.assertEqual(attach_camera_aware_fusion(
                root, timeline["source_sha256"], timeline_path), fusion)
            union = attach_candidate_review_union(root, timeline_path)
            self.assertEqual(union["review_status_counts"],
                             {"right_only_left_static_review": 1})
            self.assertEqual(attach_candidate_review_union(root, timeline_path), union)
            boards = attach_right_partial_boards(video, timeline["source_sha256"], root)
            self.assertEqual(len(boards["rows"]), 1)
            self.assertFalse(boards["rows"][0]["simulation_ready"])
            self.assertEqual(attach_right_partial_boards(
                video, timeline["source_sha256"], root), boards)
            state = attach_candidate_state_handoff(root)
            self.assertEqual(state["candidate_count"], 1)
            self.assertEqual(state["simulation_ready_count"], 0)
            self.assertEqual(attach_candidate_state_handoff(root), state)
            sequence = attach_right_board_sequence(video, timeline["source_sha256"], root)
            self.assertEqual(sequence["transition_count"], 0)
            self.assertEqual(attach_right_board_sequence(
                video, timeline["source_sha256"], root), sequence)
            left_boards = attach_left_candidate_boards(
                video, timeline["source_sha256"], root)
            self.assertEqual(left_boards["left_candidate_count"], 0)
            self.assertEqual(attach_left_candidate_boards(
                video, timeline["source_sha256"], root), left_boards)
            enriched = attach_candidate_state_handoff_v2(root)
            self.assertEqual(enriched["candidate_count"], 1)
            self.assertEqual(attach_candidate_state_handoff_v2(root), enriched)
            image_sequence = attach_candidate_image_board_sequence(
                video, timeline["source_sha256"], root)
            self.assertEqual(image_sequence["transition_count"], 0)
            self.assertEqual(attach_candidate_image_board_sequence(
                video, timeline["source_sha256"], root), image_sequence)
            ellipse = attach_candidate_house_ellipse(
                video, timeline["source_sha256"], root)
            self.assertEqual(ellipse["fitted_candidate_count"], 0)
            self.assertEqual(attach_candidate_house_ellipse(
                video, timeline["source_sha256"], root), ellipse)
            timeline["observed_events"] = [{"id": "E01", "crossing_time_s": 20}]
            timeline_path.write_text(json.dumps(timeline) + "\n")
            with self.assertRaisesRegex(ValueError, "different inputs or code"):
                attach_source_activity(video, timeline["source_sha256"],
                                       [0, 70], root, timeline_path)


if __name__ == "__main__":
    unittest.main()
