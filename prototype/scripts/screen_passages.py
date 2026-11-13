"""Screen saved passage events without mutating frozen detector outputs."""

import argparse
import json
from pathlib import Path
import sys
import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cache_contract import file_sha256
from throw_event_screening import appearance_at_crossing, SCREEN_VERSION


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--video", type=Path, required=True)
    p.add_argument("--events", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    if a.output.exists():
        p.error("Output exists; preserve earlier review artifacts")
    cv2.setNumThreads(1)
    capture = cv2.VideoCapture(str(a.video), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    fps = capture.get(cv2.CAP_PROP_FPS)
    source = json.loads(a.events.read_text())
    events = source["events"]
    results = [
        dict(
            id=e["id"],
            crossing_time_s=e["crossing_time_s"],
            colour=e["colour"],
            appearance=appearance_at_crossing(e, capture, fps),
        )
        for e in events
    ]
    capture.release()
    summary = {
        status: sum(r["appearance"]["status"] == status for r in results)
        for status in (
            "stone_appearance_candidate",
            "person_or_other_object_suspected",
            "appearance_unavailable",
        )
    }
    result = {
        "status": "development_screen_not_independent_throw_accuracy",
        "version": SCREEN_VERSION,
        "source_sha256": file_sha256(a.video),
        "original_events_sha256": file_sha256(a.events),
        "screen_sha256": file_sha256(ROOT / "prototype/throw_event_screening.py"),
        "runner_sha256": file_sha256(__file__),
        "events": results,
        "summary": summary,
        "limitations": [
            "Original events are retained; screening status is additional evidence.",
            "Brightness threshold was chosen after seeing two person-head false events and original development stones.",
            "No unseen-video precision/recall/F1 claim follows from this development check.",
            "Dark stones, lighting changes and camera changes can defeat this brightness rule.",
        ],
    }
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
