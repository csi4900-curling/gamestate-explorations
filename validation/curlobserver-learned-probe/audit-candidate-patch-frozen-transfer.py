"""Score sampled candidate-centric motion paths with a frozen patch model."""

import argparse
import json
from pathlib import Path
import sys

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cache_contract import file_sha256  # noqa: E402
from cap_patch_verifier import score_candidates  # noqa: E402
from stone_patch_detector import load_model  # noqa: E402
from vision_core import ViewCalibrator, detect_caps  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--motion", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Patch appearance audit already exists")
    motion = json.loads(args.motion.read_text())
    if file_sha256(args.video) != motion["high_resolution_source_sha256"]:
        parser.error("Video differs from candidate motion audit")
    model = load_model(args.model)
    cfg = json.loads((ROOT / "prototype/vision/annotations/calibration.json").read_text())["views"]
    refined = json.loads((ROOT / "prototype/rectification/calibration.json").read_text())
    calibrators = {}
    for name in ("left", "right"):
        view = dict(cfg[name])
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
        for event in motion["rows"]:
            path = event["selection"].get("path") or event["selection"].get("shared_prefix", [])
            if not path:
                rows.append({"candidate_id": event["candidate_id"],
                             "status": "no_selected_motion_path", "samples": []})
                continue
            sample_nodes = [path[i] for i in sorted({0, len(path) // 2, len(path) - 1})]
            cal = calibrators[event["receiving_view"]]
            samples = []
            for node in sample_nodes:
                t = node["source_time_s"]
                capture.set(cv2.CAP_PROP_POS_FRAMES,
                            round((t - motion["source_offset_s"]) * fps))
                ok, frame = capture.read()
                if not ok:
                    raise RuntimeError(f"Cannot decode source time {t}")
                H, reg = cal.register(
                    frame, max_corner_displacement_px=motion["max_corner_displacement_px"])
                record = {"source_time_s": t, "pixel_center": node["pixel_center"],
                          "registration_status": reg["status"]}
                if H is not None:
                    A = np.array(reg["reference_to_current"])
                    background = cv2.warpPerspective(
                        cal.reference, A, (frame.shape[1], frame.shape[0]))
                    caps, _ = detect_caps(frame, H, cal.view, background)
                    nearby = [p for p in caps if p["colour"] == event["colour"] and
                              np.linalg.norm(np.array(p["pixel_center"]) -
                                             node["pixel_center"]) <= 2.0]
                    if len(nearby) == 1:
                        bbox = [v / 3 for v in nearby[0]["bbox"]]
                        scored = score_candidates(frame, [{"bbox": bbox}], model)[0]
                        record.update(status="scored", patch_score=scored["patch_score"],
                                      patch_accepted=scored["patch_accepted"],
                                      cap_bbox_1080p=nearby[0]["bbox"])
                    else:
                        record.update(status="no_unique_matching_cap",
                                      matching_cap_count=len(nearby))
                else:
                    record["status"] = "registration_abstained"
                samples.append(record)
            rows.append({"candidate_id": event["candidate_id"],
                         "motion_status": event["selection"]["status"],
                         "status": "sampled_motion_path",
                         "samples": samples})
    finally:
        capture.release()
    result = {"status": "development_frozen_patch_appearance_on_candidate_motion_not_event_score",
              "motion_sha256": file_sha256(args.motion),
              "video_sha256": motion["high_resolution_source_sha256"],
              "model_sha256": file_sha256(args.model),
              "runner_sha256": file_sha256(__file__),
              "patch_code_sha256": file_sha256(ROOT / "prototype/cap_patch_verifier.py"),
              "sample_strategy": "First, midpoint, and last path node, or shared-prefix node",
              "rows": rows,
              "limitations": [
                  "The model comes from small handpicked, agent-labelled 2022 clips and is not an independent 2024 event classifier.",
                  "A stone-like patch does not prove delivery, and a weak patch does not disprove a stone.",
                  "Only three path points are sampled; appearance may change between them.",
              ]}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print([(r["candidate_id"], [round(s["patch_score"], 2)
                                for s in r["samples"] if s["status"] == "scored"])
           for r in rows])


if __name__ == "__main__":
    main()
