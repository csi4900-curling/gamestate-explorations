"""Source-review images for exposed yellow-contour continuation probes."""

import argparse
from hashlib import sha256
import json
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "korea": {
        "video": ROOT / "prototype/continuous/clip.mp4",
        "offset": 2260,
        "result": ROOT / "validation/throw-event-benchmark/canada-korea-2024/yellow-contour-continuation-development.json",
        "times": (2314, 2315, 2316, 2317, 2318, 2320),
    },
    "slovakia": {
        "video": ROOT / "validation/throw-event-benchmark/canada-slovakia-2024/source-1080p-1650-2760.mp4",
        "offset": 1650,
        "result": ROOT / "validation/throw-event-benchmark/canada-slovakia-2024/yellow-contour-continuation-development.json",
        "times": (2046, 2047, 2048, 2049, 2050, 2051),
    },
}


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", choices=sorted(SOURCES), required=True)
    args = parser.parse_args()
    cfg = SOURCES[args.target]
    result = json.loads(cfg["result"].read_text())
    if result["target_video_sha256"] != digest(cfg["video"]):
        raise ValueError("Source changed")
    paths = result["joined_image_paths"]
    if len(paths) != 1:
        raise ValueError("Expected one joined path")
    by_time = {p["time_s"]: p for p in paths[0]["points"]}
    if any(t not in by_time for t in cfg["times"]):
        raise ValueError("Selected source time missing")
    cap = cv2.VideoCapture(str(cfg["video"]), cv2.CAP_FFMPEG,
                           [cv2.CAP_PROP_N_THREADS, 1])
    panels = []
    try:
        for t in cfg["times"]:
            cap.set(cv2.CAP_PROP_POS_MSEC, (t-cfg["offset"])*1000)
            ok, frame = cap.read()
            if not ok or frame.shape[:2] != (1080, 1920):
                raise RuntimeError(f"Could not decode {t}")
            view = cv2.resize(frame[:, 960:], (480, 540),
                              interpolation=cv2.INTER_AREA)
            x, y = by_time[t]["center_1080p_px"]
            x, y = round((x-960)/2), round(y/2)
            cv2.rectangle(view, (x-13, y-13), (x+13, y+13),
                          (255, 0, 255), 2)
            cv2.rectangle(view, (0, 0), (480, 38), (10, 20, 30), -1)
            cue = "body" if "body_template" in by_time[t]["cue"] else "contour"
            cv2.putText(view, f"{t}s {cue}", (8, 27),
                        cv2.FONT_HERSHEY_SIMPLEX, .66, (255, 255, 255), 2)
            panels.append(view)
    finally:
        cap.release()
    image_path = cfg["result"].with_name("yellow-contour-continuation-source-review.jpg")
    if not cv2.imwrite(str(image_path),
                       np.vstack([np.hstack(panels[:3]), np.hstack(panels[3:])]),
                       [cv2.IMWRITE_JPEG_QUALITY, 90]):
        raise RuntimeError("Could not write image")
    manifest = {
        "status": "same_agent_source_review_of_postreview_contour_continuation",
        "result_sha256": digest(cfg["result"]),
        "video_sha256": digest(cfg["video"]),
        "runner_sha256": digest(Path(__file__)),
        "image_sha256": digest(image_path),
        "source_times_s": cfg["times"],
        "same_agent_source_review": "boxes_follow_apparent_yellow_stone_then_still_looking_stone",
        "physical_same_stone_identity_independently_verified": False,
        "physical_stop_verified": False,
    }
    image_path.with_suffix(".json").write_text(
        json.dumps(manifest, indent=2) + "\n")
    print(image_path.relative_to(ROOT))


if __name__ == "__main__":
    main()
