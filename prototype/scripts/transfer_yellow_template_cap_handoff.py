"""Run fixed yellow body-template/cap fusion on named 1080p excerpts.

Korea is a byte-for-byte regression against the development components;
Slovakia is a separate-recording, nonblind development transfer.
"""

import argparse
from hashlib import sha256
import json
from math import hypot
from pathlib import Path
import sys

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from stone_patch_detector import colour_proposals, patch_features
from scripts.audit_korea_t11_score_roi import match_low_floor, ROIS
from scripts.audit_korea_t11_sideview_patch import context_box
from scripts.fuse_korea_t11_cap_handoff import extend
from scripts.probe_latvia_1080p_body_paths import body_template, frame_at, link_paths
from scripts.scan_korea_sideview_cap_full import (
    ICE_ROI_1080P,
    NMS_CENTER_DISTANCE_1080P_PX,
    point,
)

BASE = ROOT / "validation/throw-event-benchmark"
LATVIA_TEMPLATE_VIDEO = BASE / "canada-latvia-2024/source-1080p-1650-2760.mp4"
MODEL = ROOT / "validation/curlobserver-learned-probe/sideview-patch-transfer-v1/model.npz"
TARGETS = {
    "korea-regression": {
        "video": ROOT / "prototype/continuous/clip.mp4",
        "source_sha256": "b514dd3bdd2604f39e981759626bd345288d2096b19c6bc8f1dd6cada4e326f4",
        "offset_s": 2260,
        "interval_s": (2260, 2350),
        "output": BASE / "canada-korea-2024/yellow-handoff-generic-regression.json",
    },
    "slovakia-transfer": {
        "video": BASE / "canada-slovakia-2024/source-1080p-1650-2760.mp4",
        "source_sha256": "cd5799da6d851e01c365b5f4aeeb2fb10b068e6d726d273ac129ad8f87330077",
        "offset_s": 1650,
        "interval_s": (1990, 2070),
        "output": BASE / "canada-slovakia-2024/yellow-handoff-1990-2070-development.json",
    },
}


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def run(target_name):
    cfg = TARGETS[target_name]
    if cfg["output"].exists():
        raise SystemExit("Output exists; preserve first result")
    if digest(cfg["video"]) != cfg["source_sha256"]:
        raise ValueError("Target source changed")
    reserved = json.loads((ROOT / "validation/unseen-end/reservation.json").read_text())
    if cfg["source_sha256"] == reserved["source_sha256"]:
        raise ValueError("Reserved source cannot be used for development")
    src = cv2.VideoCapture(str(LATVIA_TEMPLATE_VIDEO), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    cap = cv2.VideoCapture(str(cfg["video"]), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    if (
        not src.isOpened()
        or not cap.isOpened()
        or src.get(cv2.CAP_PROP_FPS) != 30
        or cap.get(cv2.CAP_PROP_FPS) != 30
    ):
        raise RuntimeError("Cannot open expected 30-fps videos")
    body_rows, cap_rows = [], []
    try:
        template = body_template(frame_at(src, 2310 - 1650))
        with np.load(MODEL, allow_pickle=False) as model:
            threshold = float(model["threshold"])
            start_s, stop_s = cfg["interval_s"]
            cap.set(cv2.CAP_PROP_POS_FRAMES, (start_s - cfg["offset_s"]) * 30)
            for t in range(start_s, stop_s):
                ok, frame = cap.read()
                if not ok or frame.shape[:2] != (1080, 1920):
                    raise RuntimeError(f"Could not decode {t}")
                body = match_low_floor(frame, template, ROIS["frozen"])
                supported = [p for p in body if p["matching_colour_handle_supported"]]
                body_rows.append(
                    {"time_s": t, "body_proposals": supported, "raw_body_proposal_count": len(body)}
                )
                image, proposals = colour_proposals(frame)
                positive = []
                for proposal in proposals:
                    if proposal["colour"] != "yellow":
                        continue
                    xy = point(proposal)
                    x1, y1, x2, y2 = ICE_ROI_1080P
                    if not (x1 <= xy[0] <= x2 and y1 <= xy[1] <= y2):
                        continue
                    feature = patch_features(image, context_box(proposal["bbox"]))
                    score = ((feature - model["mean"]) / model["scale"]) @ model[
                        "weights"
                    ].ravel() + model["intercept"].item()
                    if score >= threshold:
                        positive.append(
                            {
                                "center_1080p_px": xy,
                                "score": round(float(score), 5),
                                "proposal_bbox_360p": proposal["bbox"],
                            }
                        )
                accepted = []
                for p in sorted(positive, key=lambda item: -item["score"]):
                    if all(
                        hypot(
                            p["center_1080p_px"][0] - q["center_1080p_px"][0],
                            p["center_1080p_px"][1] - q["center_1080p_px"][1],
                        )
                        >= NMS_CENTER_DISTANCE_1080P_PX
                        for q in accepted
                    ):
                        accepted.append(p)
                cap_rows.append(
                    {
                        "source_time_s": t,
                        "positive_raw_proposal_count": len(positive),
                        "positive_nms_points": accepted,
                    }
                )
                if t + 1 < stop_s:
                    for _ in range(29):
                        if not cap.grab():
                            raise RuntimeError(f"Could not advance from {t}")
    finally:
        src.release()
        cap.release()
    body_paths = link_paths(body_rows)
    seeds = [p for p in body_paths if p["direction"] == "upward"]
    joined = [extend(seed, cap_rows) for seed in seeds]
    if target_name == "korea-regression":
        prior_body = json.loads(
            (BASE / "canada-korea-2024/t11-score-roi-ablation-development.json").read_text()
        )
        prior_cap = json.loads(
            (BASE / "canada-korea-2024/t11-sideview-cap-fullclip-development.json").read_text()
        )
        prior_joined = json.loads(
            (BASE / "canada-korea-2024/t11-template-to-cap-handoff-development.json").read_text()
        )
        if (
            body_paths != prior_body["variants"]["frozen_score_0.45"]["image_motion_paths"]
            or cap_rows != prior_cap["rows"]
            or joined != prior_joined["joined_image_paths"]
        ):
            raise AssertionError("Generic runner differs from Korea frozen components")
    result = {
        "status": "korea_generic_exact_component_regression"
        if target_name == "korea-regression"
        else "fixed_nonblind_cross_recording_yellow_handoff_development",
        "target_name": target_name,
        "target_video_sha256": cfg["source_sha256"],
        "template_video_sha256": digest(LATVIA_TEMPLATE_VIDEO),
        "model_sha256": digest(MODEL),
        "body_code_sha256": digest(ROOT / "prototype/scripts/audit_korea_t11_score_roi.py"),
        "cap_code_sha256": digest(ROOT / "prototype/scripts/scan_korea_sideview_cap_full.py"),
        "handoff_code_sha256": digest(ROOT / "prototype/scripts/fuse_korea_t11_cap_handoff.py"),
        "runner_sha256": digest(Path(__file__)),
        "source_time_offset_s": cfg["offset_s"],
        "source_interval_s": cfg["interval_s"],
        "sample_period_s": 1,
        "body_score_floor": 0.45,
        "body_search_xyxy_1080p": ROIS["frozen"],
        "cap_search_xyxy_1080p": ICE_ROI_1080P,
        "cap_model_score_threshold": threshold,
        "body_raw_proposal_count": sum(r["raw_body_proposal_count"] for r in body_rows),
        "body_handle_supported_count": sum(len(r["body_proposals"]) for r in body_rows),
        "cap_positive_raw_count": sum(r["positive_raw_proposal_count"] for r in cap_rows),
        "cap_positive_nms_count": sum(len(r["positive_nms_points"]) for r in cap_rows),
        "body_image_paths": body_paths,
        "joined_image_paths": joined,
        "body_supported_rows": [r for r in body_rows if r["body_proposals"]],
        "cap_positive_rows": [r for r in cap_rows if r["positive_nms_points"]],
        "limitations": [
            "Template score and cap search geometry were selected after Korea source review.",
            "No target-review positions are read by this runner, but target interval selection is nonblind.",
            "A linked image path does not verify a physical throw, stone identity, board, metric trajectory or simulation.",
            "Full-match event precision, recall and F1 require independent exhaustive labels.",
        ],
    }
    cfg["output"].write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(
        json.dumps(
            {
                "target": target_name,
                "body": result["body_raw_proposal_count"],
                "handle": result["body_handle_supported_count"],
                "cap_nms": result["cap_positive_nms_count"],
                "upward_seeds": len(seeds),
                "joined": [
                    (
                        p["seed_interval_s"],
                        p["points"][-1]["time_s"],
                        p["image_motion_interpretation"]["visual_stop_bracket_s"],
                    )
                    for p in joined
                ],
            }
        )
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", choices=sorted(TARGETS), required=True)
    run(parser.parse_args().target)


if __name__ == "__main__":
    main()
