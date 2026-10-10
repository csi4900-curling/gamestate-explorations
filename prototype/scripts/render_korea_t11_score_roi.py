"""Source review sheet for the postreview Korea T11 score/ROI ablation."""

from hashlib import sha256
import json
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "validation/throw-event-benchmark/canada-korea-2024"
VIDEO = ROOT / "prototype/continuous/clip.mp4"
AUDIT = BASE / "t11-score-roi-ablation-development.json"
TIMES = (2308, 2310, 2312, 2313, 2314, 2315)


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    audit = json.loads(AUDIT.read_text())
    if audit["target_video_sha256"] != digest(VIDEO):
        raise ValueError("T11 source differs from ablation")
    path = audit["variants"]["frozen_score_0.45"]["image_motion_paths"]
    if len(path) != 1 or path[0]["direction"] != "upward":
        raise ValueError("Low-score path set changed")
    by_time = {p["time_s"]: p for p in path[0]["points"]}
    cap = cv2.VideoCapture(str(VIDEO), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    if not cap.isOpened():
        raise RuntimeError("Cannot open source")
    panels = []
    try:
        for t in TIMES:
            cap.set(cv2.CAP_PROP_POS_MSEC, (t - 2260) * 1000)
            ok, frame = cap.read()
            if not ok or frame.shape[:2] != (1080, 1920):
                raise RuntimeError(f"Cannot decode {t}")
            view = cv2.resize(frame[:, 960:], (480, 540), interpolation=cv2.INTER_AREA)
            if t in by_time:
                x, y = by_time[t]["center_1080p_px"]
                x, y = round((x - 960) / 2), round(y / 2)
                cv2.rectangle(view, (x - 24, y - 18), (x + 24, y + 18), (255, 0, 255), 2)
            cv2.rectangle(view, (0, 0), (480, 38), (10, 20, 30), -1)
            label = f"{t}s score>=0.45 {'match' if t in by_time else 'no path'}"
            cv2.putText(view, label, (8, 27), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            panels.append(view)
    finally:
        cap.release()
    image_path = BASE / "t11-score-roi-source-review.jpg"
    if not cv2.imwrite(
        str(image_path),
        np.vstack([np.hstack(panels[:3]), np.hstack(panels[3:])]),
        [cv2.IMWRITE_JPEG_QUALITY, 90],
    ):
        raise RuntimeError("Could not write source review sheet")
    manifest = {
        "status": "same_agent_development_source_review_not_independent_event_validation",
        "audit_sha256": digest(AUDIT),
        "video_sha256": digest(VIDEO),
        "runner_sha256": digest(Path(__file__)),
        "image_sha256": digest(image_path),
        "source_times_s": TIMES,
        "same_agent_source_review": {
            "lowered_score_2308_2314": "boxes_follow_one_visible_yellow_stone_toward_house",
            "2315": "yellow_stone_remains_visible_but_no_linked_proposal",
        },
        "physical_identity_independently_verified": False,
    }
    (BASE / "t11-score-roi-source-review.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(image_path.relative_to(ROOT))


if __name__ == "__main__":
    main()
