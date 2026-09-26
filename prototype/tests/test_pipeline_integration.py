import sys
import tempfile
import unittest
from pathlib import Path
import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pipeline import analyse
from render import render


class PipelineIntegration(unittest.TestCase):
    def test_small_real_video_indexes_without_claiming_detection(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            video = folder / "sample.avi"
            writer = cv2.VideoWriter(str(video), cv2.VideoWriter_fourcc(*"MJPG"), 10, (64, 64))
            self.assertTrue(writer.isOpened())
            for i in range(20):
                writer.write(np.full((64, 64, 3), i * 10, dtype=np.uint8))
            writer.release()
            result = analyse(video, folder / "out", interval=1)
            self.assertEqual(result["sampling"]["decoded_samples"], 2)
            self.assertEqual(len(result["observations"]), 4)
            self.assertTrue(
                all(o["calibration_status"] == "unavailable" for o in result["observations"])
            )
            self.assertTrue((folder / "out/index.html").exists())

    def test_embedded_payload_cannot_close_script(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "index.html"
            render({"title": "</script><script>BAD()</script>"}, p)
            self.assertNotIn("</script><script>BAD()", p.read_text())
