"""Diagnose whether frozen learned stone-box models retain Korea T11.

Known T11 image locations are used only to diagnose missed observations.
This is postreview development data, not independent event scoring.
"""

from hashlib import sha256
import json
from pathlib import Path
import sys
from math import hypot

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from stone_patch_detector import colour_proposals, patch_features, load_model

BASE = ROOT / "validation/throw-event-benchmark/canada-korea-2024"
VIDEO = ROOT / "prototype/continuous/clip.mp4"
ABLATION = BASE / "t11-score-roi-ablation-development.json"
TRACK = ROOT / "prototype/cross-view/results.json"
MODELS = {
    "public_tracking_v2": ROOT
    / "validation/curlobserver-learned-probe/public-tracking-v2/model.npz",
    "model_v2": ROOT / "validation/curlobserver-learned-probe/model-v2/model.npz",
}
SCANS = {
    "public_tracking_v2": BASE / "t11-public-tracking-boxes-development.json",
    "model_v2": BASE / "t11-model-v2-boxes-development.json",
}
OUT = BASE / "t11-learned-box-stage-audit-development.json"
NEAR_RADIUS_1080P_PX = 40


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def center(box):
    x, y, w, h = box
    return [(x + w / 2) * 3, (y + h / 2) * 3]


def main():
    if OUT.exists():
        raise SystemExit("Output exists; preserve first stage audit")
    ablation = json.loads(ABLATION.read_text())
    scans = {name: json.loads(path.read_text()) for name, path in SCANS.items()}
    if ablation["target_video_sha256"] != digest(VIDEO) or any(
        scan["source_sha256"] != digest(VIDEO) or scan["model_sha256"] != digest(MODELS[name])
        for name, scan in scans.items()
    ):
        raise ValueError("Source or model changed")
    path = ablation["variants"]["frozen_score_0.45"]["image_motion_paths"]
    if len(path) != 1 or path[0]["direction"] != "upward":
        raise ValueError("T11 image path changed")
    expected = {
        p["time_s"]: {
            "center": p["center_1080p_px"],
            "basis": "source_reviewed_low_score_template_path",
        }
        for p in path[0]["points"]
    }
    t11 = next(row for row in json.loads(TRACK.read_text())["throws"] if row["id"] == "T11")
    for point in t11["arrival"]:
        t = point["time_s"]
        if 2315 <= t <= 2319 and t.is_integer():
            expected[int(t)] = {
                "center": [point["pixel"][0], point["pixel"][1] + 15],
                "basis": "provisional_cap_track_plus_postreview_15px_body_offset",
            }
    cap = cv2.VideoCapture(str(VIDEO), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    if not cap.isOpened():
        raise RuntimeError("Cannot open target video")
    models = {name: load_model(path) for name, path in MODELS.items()}
    rows = []
    try:
        for t, reference in sorted(expected.items()):
            cap.set(cv2.CAP_PROP_POS_MSEC, (t - 2260) * 1000)
            ok, frame = cap.read()
            if not ok or frame.shape[:2] != (1080, 1920):
                raise RuntimeError(f"Could not decode {t}")
            image, proposals = colour_proposals(frame)
            near = []
            for proposal in proposals:
                if proposal["colour"] != "yellow":
                    continue
                pixel = center(proposal["bbox"])
                distance = hypot(
                    pixel[0] - reference["center"][0], pixel[1] - reference["center"][1]
                )
                if distance <= NEAR_RADIUS_1080P_PX:
                    near.append((distance, proposal))
            near.sort(key=lambda item: item[0])
            stage = {}
            for name, model in models.items():
                boxes = scans[name]["frames"][t - 2260]["boxes"]
                accepted = [
                    box
                    for box in boxes
                    if box["colour"] == "yellow"
                    and hypot(
                        *(center(box["bbox"])[axis] - reference["center"][axis] for axis in (0, 1))
                    )
                    <= NEAR_RADIUS_1080P_PX
                ]
                scored = []
                for distance, proposal in near:
                    feature = patch_features(image, proposal["bbox"])
                    score = ((feature - model["mean"]) / model["scale"]) @ model[
                        "weights"
                    ].ravel() + model["intercept"].item()
                    scored.append((float(score), float(distance), proposal))
                scored.sort(key=lambda item: -item[0])
                stage[name] = {
                    "threshold": float(model["threshold"]),
                    "accepted_near_box_count": len(accepted),
                    "best_near_raw_proposal": {
                        "score": round(scored[0][0], 5),
                        "center_distance_1080p_px": round(scored[0][1], 2),
                        "bbox_360p": scored[0][2]["bbox"],
                    }
                    if scored
                    else None,
                    "near_raw_proposals_above_threshold": sum(
                        score >= float(model["threshold"]) for score, _, _ in scored
                    ),
                }
            rows.append(
                {
                    "source_time_s": t,
                    "expected": reference,
                    "yellow_raw_proposals_near": len(near),
                    "models": stage,
                }
            )
    finally:
        cap.release()
    result = {
        "status": "postreview_development_model_stage_audit_not_independent_truth",
        "target_video_sha256": digest(VIDEO),
        "ablation_sha256": digest(ABLATION),
        "t11_track_sha256": digest(TRACK),
        "model_sha256": {name: digest(path) for name, path in MODELS.items()},
        "full_interval_scan_sha256": {name: digest(path) for name, path in SCANS.items()},
        "box_detector_code_sha256": digest(ROOT / "prototype/stone_patch_detector.py"),
        "runner_sha256": digest(Path(__file__)),
        "near_radius_1080p_px": NEAR_RADIUS_1080P_PX,
        "rows": rows,
        "limitations": [
            "Expected T11 positions are postreview template points or a provisional cap track, not independent labels.",
            "The 40px centre-radius gate diagnoses candidate availability but is not box-IoU ground truth.",
            "Image boxes do not establish throw events, cross-view identity, or physical trajectories.",
        ],
    }
    OUT.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(
        json.dumps(
            {
                name: {
                    "near_accepted_frames": sum(
                        r["models"][name]["accepted_near_box_count"] > 0 for r in rows
                    ),
                    "near_proposal_frames": sum(r["yellow_raw_proposals_near"] > 0 for r in rows),
                    "near_raw_above_threshold_frames": sum(
                        r["models"][name]["near_raw_proposals_above_threshold"] > 0 for r in rows
                    ),
                }
                for name in models
            }
        )
    )


if __name__ == "__main__":
    main()
