"""The acceptance CLI must anchor a full-source claim to an actual video file."""

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SCORER = ROOT / "scripts/score_throw_events.py"


class ScoreThrowEventsCliTests(unittest.TestCase):
    def test_video_probe_rejects_a_matching_excerpt_declared_full(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            video = base / "source.mp4"
            subprocess.run(
                [
                    "ffmpeg",
                    "-v",
                    "error",
                    "-f",
                    "lavfi",
                    "-i",
                    "color=c=black:s=64x64:r=10:d=2",
                    "-pix_fmt",
                    "yuv420p",
                    str(video),
                ],
                check=True,
            )
            fingerprint = hashlib.sha256(video.read_bytes()).hexdigest()

            def score(declared_duration, name):
                common = {
                    "source_id": "fixture",
                    "source_sha256": fingerprint,
                    "source_interval_s": [0, declared_duration],
                    "source_duration_s": declared_duration,
                }
                reference = {
                    **common,
                    "source_duration_verified": True,
                    "reference_method": "human_independent",
                    "exhaustive": True,
                    "events": [{"id": "R1", "colour": "red", "delivery_interval_s": [0.4, 0.6]}],
                }
                prediction = {
                    **common,
                    "coverage_gaps_s": [],
                    "coverage_verified": True,
                    "events": [{"id": "P1", "colour": "red", "crossing_time_s": 0.5}],
                }
                ref_path, pred_path, out_path = (
                    base / f"{name}-{suffix}.json"
                    for suffix in ("reference", "prediction", "score")
                )
                ref_path.write_text(json.dumps(reference))
                pred_path.write_text(json.dumps(prediction))
                subprocess.run(
                    [
                        sys.executable,
                        str(SCORER),
                        "--reference",
                        str(ref_path),
                        "--predictions",
                        str(pred_path),
                        "--output",
                        str(out_path),
                        "--assess-target",
                        "--source-video",
                        str(video),
                    ],
                    check=True,
                    capture_output=True,
                    text=True,
                )
                return json.loads(out_path.read_text())

            complete = score(2, "complete")
            self.assertEqual(complete["target_assessment"]["reason"], "target_met")
            excerpt = score(1, "excerpt")
            self.assertEqual(excerpt["score"]["f1"], 1)
            self.assertEqual(
                excerpt["target_assessment"]["reason"], "unverified_full_recording_scope"
            )
            self.assertFalse(excerpt["target_assessment"]["accepted"])
            self.assertAlmostEqual(excerpt["measured_source_video_duration_s"], 2, places=2)


if __name__ == "__main__":
    unittest.main()
