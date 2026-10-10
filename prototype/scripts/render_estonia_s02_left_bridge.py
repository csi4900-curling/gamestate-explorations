"""Marked source sheet for the source-only S02 left-entry contour track."""

from hashlib import sha256
import json
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "validation/throw-event-benchmark/canada-estonia-2024"
VIDEO = BASE / "source-1080p-1650-2760.mp4"
BRIDGE = BASE / "yellow-s02-left-entry-to-prior-path-postreview.json"
TIMES = (1758.5, 1760.0, 1762.0, 1764.0, 1766.5, 1769.0, 1771.5)


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    bridge = json.loads(BRIDGE.read_text())
    if bridge["video_sha256"] != digest(VIDEO):
        raise ValueError("Source changed")
    by_time = {r["source_time_s"]: r for r in bridge["rows"]}
    if any(t not in by_time for t in TIMES):
        raise ValueError("Selected sample not in bridge")
    cap = cv2.VideoCapture(str(VIDEO), cv2.CAP_FFMPEG,
                           [cv2.CAP_PROP_N_THREADS, 1])
    panels = []
    try:
        for t in TIMES:
            cap.set(cv2.CAP_PROP_POS_MSEC, (t-1650)*1000)
            ok, frame = cap.read()
            if not ok or frame.shape[:2] != (1080, 1920):
                raise RuntimeError(f"Could not decode {t}")
            view = cv2.resize(frame[:, :960], (480, 540),
                              interpolation=cv2.INTER_AREA)
            x, y, w, h = by_time[t]["chosen"]["bbox_1080p_px"]
            cv2.rectangle(view, (round(x/2), round(y/2)),
                          (round((x+w)/2), round((y+h)/2)),
                          (255, 0, 255), 2)
            panel = np.full((574, 480, 3), (10, 20, 30), dtype=np.uint8)
            panel[34:, :] = view
            cv2.putText(panel, f"{t:.1f}s left yellow contour", (8, 25),
                        cv2.FONT_HERSHEY_SIMPLEX, .6, (255, 255, 255), 2)
            panels.append(panel)
    finally:
        cap.release()
    panels.append(np.full_like(panels[0], (30, 30, 30)))
    image_path = BASE / "yellow-s02-left-entry-bridge-source-review.jpg"
    if not cv2.imwrite(str(image_path),
                       np.vstack([np.hstack(panels[:4]), np.hstack(panels[4:])]),
                       [cv2.IMWRITE_JPEG_QUALITY, 92]):
        raise RuntimeError("Could not write bridge sheet")
    manifest = {
        "status": "same_agent_postreview_left_entry_bridge_source_review",
        "bridge_sha256": digest(BRIDGE),
        "video_sha256": digest(VIDEO),
        "runner_sha256": digest(Path(__file__)),
        "image_sha256": digest(image_path),
        "source_times_s": TIMES,
        "same_agent_source_review": "pending_visual_inspection",
        "physical_cross_view_identity_independently_verified": False,
    }
    (BASE / "yellow-s02-left-entry-bridge-source-review.json").write_text(
        json.dumps(manifest, indent=2) + "\n")
    print(image_path.relative_to(ROOT))


if __name__ == "__main__":
    main()
