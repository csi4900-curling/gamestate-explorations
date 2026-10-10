"""First fixed Korea/Slovakia yellow-contour transfer to Estonia 1720–1800 s."""

from hashlib import sha256
import json
from pathlib import Path
import sys

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from scripts.audit_korea_t11_score_roi import match_low_floor, ROIS
from scripts.continue_yellow_by_contour import yellow_contours, continue_path
from scripts.probe_latvia_1080p_body_paths import body_template, frame_at, link_paths

VIDEO = ROOT / "validation/throw-event-benchmark/canada-estonia-2024/source-1080p-1650-2760.mp4"
LATVIA = ROOT / "validation/throw-event-benchmark/canada-latvia-2024/source-1080p-1650-2760.mp4"
OUT = ROOT / "validation/throw-event-benchmark/canada-estonia-2024/yellow-contour-1720-1800-first-transfer.json"
SOURCE_SHA256 = "eaa88f73b56ea982808468a642ad5481428e758881f41cfaf812be58f949a533"
START_S, STOP_S, OFFSET_S = 1720, 1800, 1650


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    if OUT.exists():
        raise SystemExit("Output exists; preserve first Estonia transfer")
    if digest(VIDEO) != SOURCE_SHA256:
        raise ValueError("Estonia source changed")
    reserved = json.loads((ROOT / "validation/unseen-end/reservation.json").read_text())
    if SOURCE_SHA256 == reserved["source_sha256"]:
        raise ValueError("Reserved source cannot be used for development")
    source = cv2.VideoCapture(str(LATVIA), cv2.CAP_FFMPEG,
                              [cv2.CAP_PROP_N_THREADS, 1])
    cap = cv2.VideoCapture(str(VIDEO), cv2.CAP_FFMPEG,
                           [cv2.CAP_PROP_N_THREADS, 1])
    if not source.isOpened() or not cap.isOpened() or \
            source.get(cv2.CAP_PROP_FPS) != 30 or cap.get(cv2.CAP_PROP_FPS) != 30:
        raise RuntimeError("Cannot open expected 30-fps clips")
    body_rows, contour_rows = [], []
    try:
        template = body_template(frame_at(source, 2310-1650))
        cap.set(cv2.CAP_PROP_POS_FRAMES, (START_S-OFFSET_S)*30)
        for t in range(START_S, STOP_S):
            ok, frame = cap.read()
            if not ok or frame.shape[:2] != (1080, 1920):
                raise RuntimeError(f"Could not decode {t}")
            body = match_low_floor(frame, template, ROIS["frozen"])
            body_rows.append({"time_s": t,
                              "raw_body_count": len(body),
                              "body_proposals": [p for p in body
                                                 if p["matching_colour_handle_supported"]]})
            contour_rows.append({"source_time_s": t,
                                 "raw_yellow_handle_contours": yellow_contours(frame)})
            if t+1 < STOP_S:
                for _ in range(29):
                    if not cap.grab():
                        raise RuntimeError(f"Could not advance from {t}")
    finally:
        source.release()
        cap.release()
    body_paths = link_paths(body_rows)
    seeds = [p for p in body_paths if p["direction"] == "upward"]
    joined = [continue_path(seed, contour_rows) for seed in seeds]
    result = {
        "status": "first_fixed_nonblind_estonia_yellow_contour_development_transfer",
        "target_video_sha256": SOURCE_SHA256,
        "latvia_template_video_sha256": digest(LATVIA),
        "body_code_sha256": digest(ROOT / "prototype/scripts/audit_korea_t11_score_roi.py"),
        "contour_code_sha256": digest(ROOT / "prototype/scripts/continue_yellow_by_contour.py"),
        "linker_code_sha256": digest(ROOT / "prototype/scripts/probe_latvia_1080p_body_paths.py"),
        "runner_sha256": digest(Path(__file__)),
        "source_interval_s": [START_S, STOP_S],
        "source_time_offset_s": OFFSET_S,
        "sample_period_s": 1,
        "body_score_floor": 0.45,
        "body_search_xyxy_1080p": ROIS["frozen"],
        "body_raw_proposal_count": sum(r["raw_body_count"] for r in body_rows),
        "body_handle_supported_count": sum(len(r["body_proposals"]) for r in body_rows),
        "raw_contour_count": sum(len(r["raw_yellow_handle_contours"]) for r in contour_rows),
        "body_image_paths": body_paths,
        "joined_image_paths": joined,
        "body_supported_rows": [r for r in body_rows if r["body_proposals"]],
        "contour_rows_with_points": [r for r in contour_rows if r["raw_yellow_handle_contours"]],
        "limitations": [
            "The selected interval contains a previously known provisional yellow left-view candidate, so it is nonblind.",
            "The detector reads no left-candidate position and no source-review class or label.",
            "Stone identity, physical stop, board state, metric path, spin and simulation readiness are unverified.",
            "One selected window cannot measure complete-video event precision, recall or F1.",
        ],
    }
    OUT.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"body": result["body_raw_proposal_count"],
                      "handle": result["body_handle_supported_count"],
                      "contours": result["raw_contour_count"],
                      "upward_seeds": len(seeds),
                      "joined": [(p["seed_interval_s"],p["points"][-1]["time_s"],
                                  p["image_motion_interpretation"]["visual_stop_bracket_s"])
                                 for p in joined]}))


if __name__ == "__main__":
    main()
