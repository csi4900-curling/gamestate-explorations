"""Apply the frozen stone-patch screen to one paired left-bound path.

This is an exposed-recording development audit. It does not run global
cross-candidate deduplication or establish physical throw identity.
"""

import argparse
import json
from pathlib import Path
import sys

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cache_contract import file_sha256  # noqa: E402
from candidate_motion_patch_screen import screen_candidate  # noqa: E402
from cap_patch_verifier import score_candidates  # noqa: E402
from stone_patch_detector import load_model  # noqa: E402
from vision_core import ViewCalibrator, detect_caps  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--probe", type=Path, required=True)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--case", choices=("base", "extended"),
                        default="extended")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists")
    probe = json.loads(args.probe.read_text())
    if file_sha256(args.video) != probe["source_sha256"]:
        parser.error("Video differs from bound probe")
    selected = probe["cases"][args.case]
    path = selected["selection"].get("path", [])
    cfg_path = ROOT / "prototype/vision/annotations/calibration.json"
    rect_path = ROOT / "prototype/rectification/calibration.json"
    view = dict(json.loads(cfg_path.read_text())["views"]["left"])
    view["world_bounds"] = selected["world_bounds_m"]
    cal = ViewCalibrator(view, ROOT / "prototype/vision/frames")
    cal.H = np.array(json.loads(rect_path.read_text())["left"]["refined_H"])
    model = load_model(args.model)
    capture = cv2.VideoCapture(str(args.video), cv2.CAP_FFMPEG,
                               [cv2.CAP_PROP_N_THREADS, 1])
    if not capture.isOpened():
        parser.error("Cannot open video")
    fps = capture.get(cv2.CAP_PROP_FPS)
    samples = []
    try:
        if path:
            nodes = [path[index] for index in sorted({0, len(path) // 2,
                                                      len(path) - 1})]
            for node in nodes:
                t = node["source_time_s"]
                capture.set(cv2.CAP_PROP_POS_FRAMES,
                            round((t - probe["source_offset_s"]) * fps))
                ok, frame = capture.read()
                if not ok:
                    raise RuntimeError(f"Cannot decode {t}")
                H, registration = cal.register(
                    frame, max_corner_displacement_px=160)
                record = {"source_time_s": t,
                          "pixel_center": node["pixel_center"],
                          "registration_status": registration["status"]}
                if H is None:
                    record["status"] = "registration_abstained"
                else:
                    A = np.array(registration["reference_to_current"])
                    background = cv2.warpPerspective(
                        cal.reference, A, (frame.shape[1], frame.shape[0]))
                    caps, _ = detect_caps(frame, H, view, background)
                    matching = [cap for cap in caps
                                if cap["colour"] == probe["colour"] and
                                np.linalg.norm(np.array(cap["pixel_center"]) -
                                               node["pixel_center"]) <= 2.0]
                    if len(matching) == 1:
                        bbox = [value / 3 for value in matching[0]["bbox"]]
                        scored = score_candidates(
                            frame, [{"bbox": bbox}], model)[0]
                        record.update(status="scored",
                                      patch_score=scored["patch_score"],
                                      patch_accepted=scored["patch_accepted"],
                                      cap_bbox_1080p=matching[0]["bbox"])
                    else:
                        record.update(status="no_unique_matching_cap",
                                      matching_cap_count=len(matching))
                samples.append(record)
    finally:
        capture.release()
    motion = {"candidate_id": probe["candidate_id"],
              "selection": selected["selection"]}
    patch = {"candidate_id": probe["candidate_id"], "samples": samples}
    decision = screen_candidate(motion, patch)
    output = {
        "status": "postscore_isolated_bound_path_patch_not_full_event_screen",
        "candidate_id": probe["candidate_id"],
        "case": args.case,
        "probe_sha256": file_sha256(args.probe),
        "video_sha256": probe["source_sha256"],
        "model_sha256": file_sha256(args.model),
        "calibration_sha256": file_sha256(cfg_path),
        "rectification_sha256": file_sha256(rect_path),
        "patch_code_sha256": file_sha256(ROOT / "prototype/cap_patch_verifier.py"),
        "screen_code_sha256": file_sha256(
            ROOT / "prototype/candidate_motion_patch_screen.py"),
        "runner_sha256": file_sha256(Path(__file__)),
        "world_bounds_m": selected["world_bounds_m"],
        "samples": samples,
        "decision": decision,
        "limitations": [
            "The model was trained on small handpicked agent-labelled crops, not independent throw truth.",
            "One positive patch can provisionally accept a path but does not prove stone identity throughout it.",
            "This isolated check omits cross-candidate duplicate suppression and full-match scoring.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n")
    print(probe["candidate_id"], args.case, decision)


if __name__ == "__main__":
    main()
