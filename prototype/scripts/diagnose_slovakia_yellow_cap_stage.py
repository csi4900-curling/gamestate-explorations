"""Postresult cap-proposal diagnosis around the Slovakia yellow body path."""

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
from scripts.audit_korea_t11_sideview_patch import context_box
from scripts.scan_korea_sideview_cap_full import point

BASE = ROOT / "validation/throw-event-benchmark/canada-slovakia-2024"
VIDEO = BASE / "source-1080p-1650-2760.mp4"
TRANSFER = BASE / "yellow-handoff-1990-2070-development.json"
MODEL = ROOT / "validation/curlobserver-learned-probe/sideview-patch-transfer-v1/model.npz"
OUT = BASE / "yellow-handoff-cap-stage-postresult.json"
RADIUS_1080P_PX = 55


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    if OUT.exists():
        raise SystemExit("Output exists; preserve first postresult diagnosis")
    transfer = json.loads(TRANSFER.read_text())
    if transfer["target_video_sha256"] != digest(VIDEO):
        raise ValueError("Source changed")
    paths = [p for p in transfer["body_image_paths"] if p["direction"] == "upward"]
    if len(paths) != 1:
        raise ValueError("Expected one upward body path")
    cap = cv2.VideoCapture(str(VIDEO), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    rows = []
    try:
        with np.load(MODEL, allow_pickle=False) as model:
            threshold = float(model["threshold"])
            for p in paths[0]["points"]:
                t = p["time_s"]
                cap.set(cv2.CAP_PROP_POS_MSEC, (t - 1650) * 1000)
                ok, frame = cap.read()
                if not ok or frame.shape[:2] != (1080, 1920):
                    raise RuntimeError(f"Could not decode {t}")
                image, proposals = colour_proposals(frame)
                nearby = []
                for proposal in proposals:
                    if proposal["colour"] != "yellow":
                        continue
                    xy = point(proposal)
                    distance = hypot(
                        xy[0] - p["center_1080p_px"][0], xy[1] - p["center_1080p_px"][1]
                    )
                    if distance > RADIUS_1080P_PX:
                        continue
                    feature = patch_features(image, context_box(proposal["bbox"]))
                    score = ((feature - model["mean"]) / model["scale"]) @ model[
                        "weights"
                    ].ravel() + model["intercept"].item()
                    nearby.append(
                        {
                            "score": round(float(score), 5),
                            "center_1080p_px": xy,
                            "center_distance_1080p_px": round(distance, 2),
                        }
                    )
                nearby.sort(key=lambda x: -x["score"])
                rows.append(
                    {
                        "source_time_s": t,
                        "body_center_1080p_px": p["center_1080p_px"],
                        "nearby_raw_yellow_proposal_count": len(nearby),
                        "best_nearby": nearby[0] if nearby else None,
                        "nearby_above_frozen_threshold": bool(
                            nearby and nearby[0]["score"] >= threshold
                        ),
                    }
                )
    finally:
        cap.release()
    result = {
        "status": "postresult_positioned_stage_diagnosis_not_detector_output",
        "target_video_sha256": digest(VIDEO),
        "transfer_sha256": digest(TRANSFER),
        "model_sha256": digest(MODEL),
        "feature_code_sha256": digest(ROOT / "prototype/stone_patch_detector.py"),
        "runner_sha256": digest(Path(__file__)),
        "near_radius_1080p_px": RADIUS_1080P_PX,
        "frozen_model_threshold": threshold,
        "rows": rows,
        "limitations": [
            "Body-path positions were known before this stage diagnosis and are not available to the runtime cap scanner.",
            "Nearby proposals are not independently labelled stone boxes.",
            "This selected moving path cannot measure cap false positives, event recall or game state.",
        ],
    }
    OUT.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(
        json.dumps(
            {
                "near_proposal_frames": sum(
                    r["nearby_raw_yellow_proposal_count"] > 0 for r in rows
                ),
                "above_threshold_frames": sum(r["nearby_above_frozen_threshold"] for r in rows),
                "total_frames": len(rows),
            }
        )
    )


if __name__ == "__main__":
    main()
