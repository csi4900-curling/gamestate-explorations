"""Render the cross-match partial T11 body-template path and its loss."""

from hashlib import sha256
import json
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "validation/throw-event-benchmark/canada-korea-2024"
VIDEO = ROOT / "prototype/continuous/clip.mp4"
AUDIT = BASE / "latvia-body-template-transfer-v2-development.json"
TIMES = (2308, 2309, 2310, 2311, 2312, 2313)


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    result = json.loads(AUDIT.read_text())
    if result["target_video_sha256"] != digest(VIDEO):
        raise ValueError("T11 source differs from transfer")
    yellow_paths = result["image_motion_paths"]["yellow"]
    if len(yellow_paths) != 1 or yellow_paths[0]["direction"] != "upward":
        raise ValueError("T11 upward-path set changed")
    path = yellow_paths[0]
    by_time = {p["time_s"]: p for p in path["points"]}
    capture = cv2.VideoCapture(str(VIDEO), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    panels = []
    try:
        for t in TIMES:
            capture.set(cv2.CAP_PROP_POS_MSEC, (t - 2260) * 1000)
            ok, frame = capture.read()
            if not ok:
                raise RuntimeError(f"Cannot decode {t}")
            view = cv2.resize(frame[:, 960:], (480, 540), interpolation=cv2.INTER_AREA)
            if t in by_time:
                x, y = by_time[t]["center_1080p_px"]
                x, y = round((x - 960) / 2), round(y / 2)
                cv2.rectangle(view, (x - 24, y - 18), (x + 24, y + 18), (255, 0, 255), 2)
            cv2.rectangle(view, (0, 0), (480, 38), (10, 20, 30), -1)
            cv2.putText(
                view,
                f"{t}s {'matched' if t in by_time else 'visible/no match'}",
                (8, 27),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                (255, 255, 255),
                2,
            )
            panels.append(view)
    finally:
        capture.release()
    image_path = BASE / "latvia-template-t11-source-review.jpg"
    if not cv2.imwrite(
        str(image_path),
        np.vstack([np.hstack(panels[:3]), np.hstack(panels[3:])]),
        [cv2.IMWRITE_JPEG_QUALITY, 90],
    ):
        raise RuntimeError("Could not write source sheet")
    manifest = {
        "status": "same_agent_cross_match_source_review_not_independent_event_validation",
        "audit_sha256": digest(AUDIT),
        "video_sha256": digest(VIDEO),
        "runner_sha256": digest(Path(__file__)),
        "image_sha256": digest(image_path),
        "source_times_s": TIMES,
        "upward_path_id": path["diagnostic_path_id"],
        "same_agent_source_review": {
            "matched_2308_2311": "one_source_visible_yellow_stone_moving_toward_house",
            "visible_unmatched_2312_2313": "same_yellow_stone_visible_but_body_template_has_no_supported_box",
        },
        "physical_identity_independently_verified": False,
    }
    (BASE / "latvia-template-t11-source-review.json").write_text(
        json.dumps(manifest, indent=2) + "\n"
    )
    print(image_path.relative_to(ROOT))


if __name__ == "__main__":
    main()
