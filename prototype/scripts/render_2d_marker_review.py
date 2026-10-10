"""Render one source scoreboard crop per recognized end in each 2D scan."""

from hashlib import sha256
import json
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "validation/throw-event-benchmark"
OUT = BASE / "layout-router/full-2024-coverage"


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    outputs = []
    for name in ("latvia", "scotland"):
        video = BASE / f"canada-{name}-2024/source-360p.mp4"
        scan_path = BASE / f"canada-{name}-2024/end-marker-full-2d-local-development.json"
        scan = json.loads(scan_path.read_text())
        if scan["video_sha256"] != digest(video):
            raise ValueError(f"Source differs for {name}")
        cap = cv2.VideoCapture(str(video), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
        fps = cap.get(cv2.CAP_PROP_FPS)
        panels, examples = [], []
        for end in sorted(int(value) for value in scan["recognized_end_counts"]):
            hits = [row for row in scan["samples"] if row["marker"] and row["marker"]["end"] == end]
            chosen = hits[len(hits) // 2]
            time_s = chosen["time_s"]
            cap.set(cv2.CAP_PROP_POS_FRAMES, round(time_s * fps))
            ok, frame = cap.read()
            if not ok:
                raise RuntimeError(f"Could not decode {name} at {time_s}")
            crop = frame[34:110, 375:580]
            enlarged = cv2.resize(crop, None, fx=3, fy=3, interpolation=cv2.INTER_NEAREST)
            panel = np.full((258, 615, 3), 255, dtype=np.uint8)
            panel[30:] = enlarged
            cv2.putText(
                panel,
                f"{name} {time_s}s reader end {end}",
                (5, 20),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 0, 0),
                1,
            )
            panels.append(panel)
            examples.append(
                {
                    "source_time_s": time_s,
                    "reader_end": end,
                    "reader_colour": chosen["marker"]["colour"],
                    "source_crop_xyxy_px": [375, 34, 580, 110],
                }
            )
        cap.release()
        blank = np.full_like(panels[0], 255)
        while len(panels) < 8:
            panels.append(blank)
        sheet = np.vstack([np.hstack(panels[index : index + 2]) for index in (0, 2, 4, 6)])
        image_path = OUT / f"{name}-2d-marker-source-review.jpg"
        if not cv2.imwrite(str(image_path), sheet):
            raise RuntimeError(f"Could not write {image_path}")
        outputs.append(
            {
                "match": name,
                "video_sha256": scan["video_sha256"],
                "scan_sha256": digest(scan_path),
                "image_path": str(image_path.relative_to(ROOT)),
                "image_sha256": digest(image_path),
                "examples": examples,
            }
        )
    result = {
        "status": "prediction_exposed_source_crop_review_not_independent_validation",
        "runner_sha256": digest(Path(__file__)),
        "games": outputs,
        "limitations": [
            "One selected positive marker per recognized end cannot establish full-scan accuracy.",
            "Visible displayed-end markers are not physical end or throw timestamps.",
        ],
    }
    (OUT / "2d-marker-source-review.json").write_text(json.dumps(result, indent=2) + "\n")
    print([row["image_path"] for row in outputs])


if __name__ == "__main__":
    main()
