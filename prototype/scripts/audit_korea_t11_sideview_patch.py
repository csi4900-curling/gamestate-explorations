"""Frozen side-view cap-patch score on source-reviewed Korea T11 positions.

Postreview candidate selection diagnoses appearance transfer. It is not an
independent frame, object, or throw-event evaluation.
"""

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

BASE = ROOT / "validation/throw-event-benchmark/canada-korea-2024"
VIDEO = ROOT / "prototype/continuous/clip.mp4"
STAGE = BASE / "t11-learned-box-stage-audit-development.json"
MODEL = ROOT / "validation/curlobserver-learned-probe/sideview-patch-transfer-v1/model.npz"
OUT = BASE / "t11-sideview-cap-patch-development.json"


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def context_box(box):
    # Exactly the crop geometry from build_cap_patch_review.crop_with_context.
    x, y, w, h = box
    side = max(48, min(210, round(3.0 * max(w, h))))
    cx, cy = x + w / 2, y + h / 2 + side * 0.13
    return [round(cx - side / 2), round(cy - side / 2), side, side]


def main():
    if OUT.exists():
        raise SystemExit("Output exists; preserve first transfer diagnostic")
    stage = json.loads(STAGE.read_text())
    if stage["target_video_sha256"] != digest(VIDEO):
        raise ValueError("T11 source changed")
    cap = cv2.VideoCapture(str(VIDEO), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    if not cap.isOpened():
        raise RuntimeError("Cannot open video")
    rows = []
    try:
        with np.load(MODEL, allow_pickle=False) as model:
            threshold = float(model["threshold"])
            for ref in stage["rows"]:
                t = ref["source_time_s"]
                cap.set(cv2.CAP_PROP_POS_MSEC, (t - 2260) * 1000)
                ok, frame = cap.read()
                if not ok or frame.shape[:2] != (1080, 1920):
                    raise RuntimeError(f"Could not decode {t}")
                image, proposals = colour_proposals(frame)
                nearby = []
                for proposal in proposals:
                    if proposal["colour"] != "yellow":
                        continue
                    x, y, w, h = proposal["bbox"]
                    dist = hypot(
                        3 * (x + w / 2) - ref["expected"]["center"][0],
                        3 * (y + h / 2) - ref["expected"]["center"][1],
                    )
                    if dist > stage["near_radius_1080p_px"]:
                        continue
                    bbox = context_box(proposal["bbox"])
                    feature = patch_features(image, bbox)
                    score = ((feature - model["mean"]) / model["scale"]) @ model[
                        "weights"
                    ].ravel() + model["intercept"].item()
                    nearby.append(
                        {
                            "score": round(float(score), 5),
                            "center_distance_1080p_px": round(dist, 2),
                            "proposal_bbox_360p": proposal["bbox"],
                            "context_bbox_360p": bbox,
                        }
                    )
                nearby.sort(key=lambda p: -p["score"])
                rows.append(
                    {
                        "source_time_s": t,
                        "expected_position_basis": ref["expected"]["basis"],
                        "nearby_raw_yellow_proposals": len(nearby),
                        "best_nearby": nearby[0] if nearby else None,
                        "any_nearby_above_frozen_threshold": bool(
                            nearby and nearby[0]["score"] >= threshold
                        ),
                    }
                )
    finally:
        cap.release()
    result = {
        "status": "postreview_development_cap_patch_score_not_detector_output",
        "target_video_sha256": digest(VIDEO),
        "stage_audit_sha256": digest(STAGE),
        "model_sha256": digest(MODEL),
        "feature_code_sha256": digest(ROOT / "prototype/stone_patch_detector.py"),
        "crop_geometry_code_sha256": digest(ROOT / "prototype/scripts/build_cap_patch_review.py"),
        "runner_sha256": digest(Path(__file__)),
        "threshold": threshold,
        "near_radius_1080p_px": stage["near_radius_1080p_px"],
        "rows": rows,
        "nearby_positive_frame_count": sum(
            row["any_nearby_above_frozen_threshold"] for row in rows
        ),
        "limitations": [
            "Near T11 proposals were selected with reviewed positions, which a real detector cannot use.",
            "This cap-context verifier was trained on selected China crops and did not learn full-video background rejection here.",
            "Accepted appearance proposals do not establish moving-stone identity, release, or event F1.",
        ],
    }
    OUT.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(
        json.dumps(
            {
                "nearby_positive_frames": result["nearby_positive_frame_count"],
                "sampled_frames": len(rows),
            }
        )
    )


if __name__ == "__main__":
    main()
