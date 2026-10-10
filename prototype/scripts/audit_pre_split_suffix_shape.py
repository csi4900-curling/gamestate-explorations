"""Compare source proposal shapes for baseline and suffix-added board objects."""

import argparse
from collections import Counter
import json
from math import dist
from pathlib import Path
import sys

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from body_localization import detect_and_localize, transported_reference_camera  # noqa: E402
from cache_contract import file_sha256  # noqa: E402
from vision_core import ViewCalibrator  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("video", "boards", "suffix", "motion", "output"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Shape audit output already exists")
    boards = json.loads(args.boards.read_text())
    suffix = json.loads(args.suffix.read_text())
    motion = json.loads(args.motion.read_text())
    if (suffix["parent_boards_sha256"] != file_sha256(args.boards) or
            motion["high_resolution_source_sha256"] != file_sha256(args.video) or
            boards["high_resolution_source_sha256"] != file_sha256(args.video)):
        parser.error("Input provenance differs")
    board_by = {row["candidate_id"]: row for row in boards["rows"]}
    views = json.loads((ROOT / "prototype/vision/annotations/calibration.json").read_text())["views"]
    refined = json.loads((ROOT / "prototype/rectification/calibration.json").read_text())
    calibrators = {}
    for name in ("left", "right"):
        view = dict(views[name])
        if name == "right":
            view["world_bounds"] = [-2.375, -1.975, 2.375, 22.0]
        cal = ViewCalibrator(view, ROOT / "prototype/vision/frames")
        cal.H = np.array(refined[name]["refined_H"])
        calibrators[name] = cal
    capture = cv2.VideoCapture(str(args.video), cv2.CAP_FFMPEG,
                               [cv2.CAP_PROP_N_THREADS, 1])
    if not capture.isOpened():
        parser.error("Cannot open video")
    fps = capture.get(cv2.CAP_PROP_FPS)
    rows = []
    try:
        for suffix_row in suffix["rows"]:
            pid = suffix_row["candidate_id"]
            original = board_by[pid]
            added_ids = {stone["local_observation_id"]
                         for stone in suffix_row["added_observations"]}
            for stone in suffix_row["suffix_board"]["stones"]:
                t = stone["last_seen_s"]
                frame_record = next(row for row in original["frames"]
                                    if row["source_time_s"] == t)
                matches = [p for p in frame_record["stones"]
                           if p["colour"] == stone["colour"] and
                           dist(p["view_local_ground_position_m"],
                                stone["view_local_ground_position_m"]) <= 0.18]
                if len(matches) != 1:
                    raise ValueError(f"Stored frame match differs: {pid} {t}")
                center = matches[0]["pixel_center"]
                capture.set(cv2.CAP_PROP_POS_FRAMES,
                            round((t - motion["source_offset_s"]) * fps))
                ok, image = capture.read()
                if not ok:
                    raise RuntimeError(f"Cannot decode {t}")
                cal = calibrators[original["receiving_view"]]
                H, registration = cal.register(
                    image, max_corner_displacement_px=motion[
                        "max_corner_displacement_px"])
                if H is None:
                    raise ValueError(f"Frame no longer registers: {pid} {t}")
                A = np.array(registration["reference_to_current"])
                background = cv2.warpPerspective(
                    cal.reference, A, (image.shape[1], image.shape[0]))
                prior = transported_reference_camera(cal.H, H, cal.view["region"])
                found, _ = detect_and_localize(image, H, cal.view, background, prior)
                close = [p for p in found if p["colour"] == stone["colour"] and
                         np.linalg.norm(np.array(p["pixel_center"]) - center) <= 2.0]
                if len(close) != 1:
                    raise ValueError(f"Decoded proposal match differs: {pid} {t}")
                proposal = close[0]
                x, y, width, height = proposal["bbox"]
                rows.append({
                    "candidate_id": pid,
                    "local_observation_id": stone["local_observation_id"],
                    "added_by_suffix": stone["local_observation_id"] in added_ids,
                    "colour": stone["colour"],
                    "source_time_s": t,
                    "pixel_center": proposal["pixel_center"],
                    "bbox": [x, y, width, height],
                    "colour_component_height_width_ratio": round(height / width, 4),
                    "body_support": proposal.get("body_support"),
                    "proposal_kind": proposal["proposal_kind"],
                })
    finally:
        capture.release()
    output = {
        "status": "development_source_shape_audit_not_validated_board_classifier",
        "input_sha256": {key: file_sha256(getattr(args, key)) for key in
                         ("video", "boards", "suffix", "motion")},
        "runner_sha256": file_sha256(Path(__file__)),
        "count_by_proposal_kind": dict(Counter(row["proposal_kind"] for row in rows)),
        "row_count": len(rows),
        "rows": rows,
        "limitations": [
            "The two suffix additions were source-inspected before this diagnostic; any shape threshold is postscore development.",
            "A single image shape does not establish whether an object is a curling stone across views or occlusions.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n")
    print(len(rows), "shapes", output["count_by_proposal_kind"])


if __name__ == "__main__":
    main()
