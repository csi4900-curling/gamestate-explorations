"""Check 360p split-panel registration on Latvia held and moving paths."""

from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import sys

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from lowres_split_panel_camera_registration import source_pair  # noqa: E402

BASE = ROOT / "validation/throw-event-benchmark/canada-latvia-2024"
LANE = ROOT / "validation/throw-event-benchmark/layout-router/full-2024-coverage/latvia24-full-v1"
VIDEO = BASE / "source-360p.mp4"
JOIN = BASE / "end6-cross-resolution-body-cap-development.json"
MOVING = BASE / "end6-split-panel-registration-czech-rule-transfer-development.json"
QUIET = BASE / "end6-split-panel-registration-held-path-controls-development.json"
YELLOW = LANE / "end6-highres-body-handle-screen-development.json"
RED = LANE / "end6-highres-red-full-transfer-development.json"
OUT = BASE / "end6-lowres-split-registration-transfer-development.json"


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def main():
    if OUT.exists():
        raise ValueError("Latvia low-resolution transfer already exists")
    join, moving, quiet, yellow, red = (
        json.loads(p.read_text()) for p in
        (JOIN, MOVING, QUIET, YELLOW, RED))
    source_hash = digest(VIDEO)
    if (source_hash != join["lowres_source_sha256"] or
            moving["join_sha256"] != digest(JOIN) or
            quiet["join_sha256"] != digest(JOIN) or
            moving["source_video_sha256"] !=
            join["highres_source_sha256"] or
            quiet["source_video_sha256"] !=
            join["highres_source_sha256"] or
            yellow["blind_video_sha256"] !=
            join["highres_source_sha256"] or
            red["source_video_sha256"] != join["highres_source_sha256"] or
            moving["registration_code_sha256"] != digest(ROOT /
                "prototype/split_panel_camera_registration.py")):
        raise ValueError("Latvia source or frozen high-res lineage differs")
    cap = cv2.VideoCapture(str(VIDEO), cv2.CAP_FFMPEG,
                           [cv2.CAP_PROP_N_THREADS, 1])
    if not cap.isOpened():
        raise ValueError("Latvia 360p source unreadable")
    fps = cap.get(cv2.CAP_PROP_FPS)

    def frame_at(time_s):
        cap.set(cv2.CAP_PROP_POS_FRAMES, round(time_s * fps))
        ok, frame = cap.read()
        if not ok:
            raise ValueError(f"Frame {time_s} unreadable")
        return frame

    moving_by_id = {r["right_proposal_id"]: r for r in moving["rows"]}
    paths = {("yellow", p["diagnostic_path_id"]): p
             for p in yellow["supported_image_paths"]}
    paths.update({("red", p["diagnostic_path_id"]): p
                  for p in red["red_supported_image_paths"]})
    results = []
    try:
        for item in join["rows"]:
            if item["source_prefix_class"] != "moving_stone_pixels":
                continue
            prior = moving_by_id[item["right_proposal_id"]]
            points = item["observed_motion_onset"]["observed_moving_points"]
            if len(prior["pairs"]) != len(points) - 1:
                raise ValueError("Moving prefix pair inventory changed")
            for old, first, second in zip(prior["pairs"],
                                          points, points[1:]):
                t0, t1 = first["time_s"], second["time_s"]
                if old["interval_s"] != [t0, t1]:
                    raise ValueError("Moving prefix time mismatch")
                result = source_pair(first["pixel"], second["pixel"],
                                     t0, t1, frame_at)
                results.append({"group": "reviewed_moving_stone_pixels",
                                "id": item["right_proposal_id"],
                                "interval_s": [t0, t1],
                                "highres_residual_px": old[
                                    "camera_residual_px"],
                                "lowres": result})
        for item in quiet["rows"]:
            if item["status"] != "audited":
                continue
            path = paths[(item["colour"], item["highres_path_id"])]
            by_time = {p["time_s"]: p["center_1080p_px"]
                       for p in path["points"]}
            for old in item["pairs"]:
                t0, t1 = old["interval_s"]
                result = source_pair(
                    [v / 3 for v in by_time[t0]],
                    [v / 3 for v in by_time[t1]],
                    t0, t1, frame_at)
                results.append({"group": "preboundary_quiet_body_path",
                                "id": item["right_proposal_id"],
                                "interval_s": [t0, t1],
                                "highres_residual_px": old[
                                    "camera_residual_px"],
                                "lowres": result})
    finally:
        cap.release()
    summary = {}
    for group in ("reviewed_moving_stone_pixels", "preboundary_quiet_body_path"):
        subset = [r for r in results if r["group"] == group]
        accepted = [r for r in subset if r["lowres"][
            "camera_residual_px"] is not None]
        summary[group] = {
            "pair_count": len(subset),
            "registered_count": len(accepted),
            "residual_over_5_count": sum(r["lowres"][
                "camera_residual_px"] > 5 for r in accepted),
            "abstention_statuses": dict(Counter(r["lowres"]["subpairs"][-1][
                "status"] if r["lowres"]["subpairs"] else r["lowres"]["status"]
                for r in subset if r["lowres"]["camera_residual_px"] is None)),
        }
    if summary["reviewed_moving_stone_pixels"]["pair_count"] != 40 or \
            summary["preboundary_quiet_body_path"]["pair_count"] != 45:
        raise ValueError("Latvia path inventory differs")
    payload = {
        "status": "czech_developed_lowres_split_adapter_latvia_transfer_not_throw_truth",
        "source_video_sha256": source_hash,
        "source_1080p_sha256": join["highres_source_sha256"],
        "input_sha256": {"join": digest(JOIN), "moving": digest(MOVING),
                         "quiet": digest(QUIET), "yellow_paths": digest(YELLOW),
                         "red_paths": digest(RED)},
        "lowres_adapter_sha256": digest(ROOT /
            "prototype/lowres_split_panel_camera_registration.py"),
        "registration_code_sha256": digest(ROOT /
            "prototype/split_panel_camera_registration.py"),
        "runner_sha256": digest(Path(__file__)),
        "method": "Unchanged Czech-developed 320x360 panel crop and 2x resize, followed by frozen high-resolution panel registration; Latvia moving cap pixels from 360p and quiet high-resolution body pixels scaled by 1/3.",
        "summary_by_group": summary,
        "rows": results,
        "limitations": [
            "The paired moving and quiet paths are selected same-match development observations, not independent throw or stationarity labels.",
            "Quiet body points come from 1080p detections scaled into 360p and may not coincide exactly with low-resolution cap pixels.",
            "A camera residual and a five-pixel threshold do not identify physical release or throw completion.",
        ],
    }
    OUT.write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
