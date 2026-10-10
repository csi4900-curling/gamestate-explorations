"""Run the frozen side-view cap verifier across the full Korea T11 clip.

This scans without T11 positions. Positive boxes remain provisional objects;
no event or same-stone claim follows from this appearance score alone.
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
from scripts.audit_korea_t11_sideview_patch import context_box

VIDEO = ROOT / "prototype/continuous/clip.mp4"
MODEL = ROOT / "validation/curlobserver-learned-probe/sideview-patch-transfer-v1/model.npz"
OUT = ROOT / "validation/throw-event-benchmark/canada-korea-2024/t11-sideview-cap-fullclip-development.json"
SOURCE_START_S, SOURCE_STOP_S = 2260, 2350
ICE_ROI_1080P = (990, 400, 1890, 970)
NMS_CENTER_DISTANCE_1080P_PX = 30


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b""):
            h.update(chunk)
    return h.hexdigest()


def point(proposal):
    x, y, w, h = proposal["bbox"]
    return [3*(x+w/2), 3*(y+h/2)]


def main():
    if OUT.exists():
        raise SystemExit("Output exists; preserve first full-clip scan")
    reserved = json.loads((ROOT / "validation/unseen-end/reservation.json").read_text())
    if digest(VIDEO) == reserved["source_sha256"]:
        raise ValueError("Reserved source cannot be used for development")
    cap = cv2.VideoCapture(str(VIDEO), cv2.CAP_FFMPEG,
                           [cv2.CAP_PROP_N_THREADS, 1])
    if not cap.isOpened() or cap.get(cv2.CAP_PROP_FPS) != 30:
        raise RuntimeError("Cannot open expected 30-fps clip")
    rows = []
    try:
        with np.load(MODEL, allow_pickle=False) as model:
            threshold = float(model["threshold"])
            for t in range(SOURCE_START_S, SOURCE_STOP_S):
                ok, frame = cap.read()
                if not ok or frame.shape[:2] != (1080, 1920):
                    raise RuntimeError(f"Could not decode {t}")
                image, proposals = colour_proposals(frame)
                screened = []
                for proposal in proposals:
                    if proposal["colour"] != "yellow":
                        continue
                    xy = point(proposal)
                    x1, y1, x2, y2 = ICE_ROI_1080P
                    if not (x1 <= xy[0] <= x2 and y1 <= xy[1] <= y2):
                        continue
                    feature = patch_features(image, context_box(proposal["bbox"]))
                    score = ((feature-model["mean"])/model["scale"]) @ \
                        model["weights"].ravel() + model["intercept"].item()
                    if score >= threshold:
                        screened.append({"center_1080p_px": xy,
                                         "score": round(float(score), 5),
                                         "proposal_bbox_360p": proposal["bbox"]})
                accepted = []
                for p in sorted(screened, key=lambda item: -item["score"]):
                    if all(hypot(p["center_1080p_px"][0]-q["center_1080p_px"][0],
                                 p["center_1080p_px"][1]-q["center_1080p_px"][1])
                           >= NMS_CENTER_DISTANCE_1080P_PX for q in accepted):
                        accepted.append(p)
                rows.append({"source_time_s": t,
                             "positive_raw_proposal_count": len(screened),
                             "positive_nms_points": accepted})
                if t+1 < SOURCE_STOP_S:
                    for _ in range(29):
                        if not cap.grab():
                            raise RuntimeError(f"Could not advance from {t}")
    finally:
        cap.release()
    result = {
        "status": "full_clip_unpositioned_cap_appearance_scan_development",
        "target_video_sha256": digest(VIDEO),
        "model_sha256": digest(MODEL),
        "feature_code_sha256": digest(ROOT / "prototype/stone_patch_detector.py"),
        "context_code_sha256": digest(ROOT / "prototype/scripts/audit_korea_t11_sideview_patch.py"),
        "runner_sha256": digest(Path(__file__)),
        "source_interval_s": [SOURCE_START_S, SOURCE_STOP_S],
        "sample_period_s": 1,
        "yellow_only": True,
        "ice_roi_1080p": ICE_ROI_1080P,
        "frozen_model_score_threshold": threshold,
        "nms_center_distance_1080p_px": NMS_CENTER_DISTANCE_1080P_PX,
        "positive_raw_total": sum(r["positive_raw_proposal_count"] for r in rows),
        "positive_nms_total": sum(len(r["positive_nms_points"]) for r in rows),
        "rows": rows,
        "limitations": [
            "The ice ROI and cap context on colour-proposal boxes are postreview development choices.",
            "A positive cap patch may be a settled stone, marking, player or other object.",
            "One-hertz boxes alone do not prove a moving stone or throw event.",
        ],
    }
    OUT.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"raw": result["positive_raw_total"],
                      "nms": result["positive_nms_total"],
                      "frames": len(rows)}))


if __name__ == "__main__":
    main()
