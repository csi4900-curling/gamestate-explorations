"""Postreview score/ROI ablation for a Latvia body template on Korea T11.

All thresholds below are development diagnostics; no variant is a validated
cross-recording detector or an independent event-precision estimate.
"""

from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import sys

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype/scripts"))
from probe_latvia_1080p_body_paths import (
    body_template,
    frame_at,
    link_paths,
    MAX_PEAKS,
    NMS_SIDE_HALFRES,
)
from screen_latvia_body_with_handle import handle_evidence

LATVIA = ROOT / "validation/throw-event-benchmark/canada-latvia-2024/source-1080p-1650-2760.mp4"
VIDEO = ROOT / "prototype/continuous/clip.mp4"
BASELINE = (
    ROOT
    / "validation/throw-event-benchmark/canada-korea-2024/latvia-body-template-transfer-v2-development.json"
)
OUT = (
    ROOT
    / "validation/throw-event-benchmark/canada-korea-2024/t11-score-roi-ablation-development.json"
)
START_S, STOP_S = 2260, 2350
ROIS = {"frozen": (990, 520, 1890, 970), "wider": (990, 400, 1890, 970)}
FLOORS = (0.55, 0.45)


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def match_low_floor(frame, template, roi):
    x1, y1, x2, y2 = roi
    gray = cv2.resize(
        cv2.cvtColor(frame[y1:y2, x1:x2], cv2.COLOR_BGR2GRAY),
        ((x2 - x1) // 2, (y2 - y1) // 2),
        interpolation=cv2.INTER_AREA,
    )
    corr = cv2.matchTemplate(gray, template, cv2.TM_CCOEFF_NORMED)
    peaks = []
    for _ in range(MAX_PEAKS):
        _, score, _, (px, py) = cv2.minMaxLoc(corr)
        if score < min(FLOORS):
            break
        point = {
            "center_1080p_px": [x1 + 2 * px + 40, y1 + 2 * py + 19],
            "score": round(float(score), 5),
        }
        evidence = handle_evidence(frame, point)
        peaks.append(
            {
                **point,
                **evidence,
                "matching_colour_handle_supported": bool(
                    evidence["handle_colour_pixels"]["yellow"] >= 120
                ),
            }
        )
        cv2.rectangle(
            corr,
            (max(0, px - NMS_SIDE_HALFRES), max(0, py - NMS_SIDE_HALFRES)),
            (
                min(corr.shape[1] - 1, px + NMS_SIDE_HALFRES),
                min(corr.shape[0] - 1, py + NMS_SIDE_HALFRES),
            ),
            -1,
            thickness=-1,
        )
    return peaks


def main():
    if OUT.exists():
        raise SystemExit("Output exists; preserve ablation provenance")
    baseline = json.loads(BASELINE.read_text())
    if baseline["target_video_sha256"] != digest(VIDEO) or baseline[
        "latvia_template_video_sha256"
    ] != digest(LATVIA):
        raise ValueError("Source differs from frozen transfer")
    src = cv2.VideoCapture(str(LATVIA), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    cap = cv2.VideoCapture(str(VIDEO), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    if (
        not src.isOpened()
        or not cap.isOpened()
        or src.get(cv2.CAP_PROP_FPS) != 30
        or cap.get(cv2.CAP_PROP_FPS) != 30
    ):
        raise RuntimeError("Cannot open expected 30-fps clips")
    samples = []
    try:
        template = body_template(frame_at(src, 2310 - 1650))
        for t in range(START_S, STOP_S):
            ok, frame = cap.read()
            if not ok or frame.shape[:2] != (1080, 1920):
                raise RuntimeError(f"Could not decode {t}")
            samples.append(
                {
                    "time_s": t,
                    "peaks": {
                        name: match_low_floor(frame, template, roi) for name, roi in ROIS.items()
                    },
                }
            )
            if t + 1 < STOP_S:
                for _ in range(29):
                    if not cap.grab():
                        raise RuntimeError(f"Could not advance from {t}")
    finally:
        src.release()
        cap.release()

    variants = {}
    for roi_name in ROIS:
        for floor in FLOORS:
            name = f"{roi_name}_score_{floor:.2f}"
            rows = [
                {
                    "time_s": row["time_s"],
                    "body_proposals": [
                        p
                        for p in row["peaks"][roi_name]
                        if p["score"] >= floor and p["handle_colour_pixels"]["yellow"] >= 120
                    ],
                }
                for row in samples
            ]
            paths = link_paths(rows)
            variants[name] = {
                "roi_xyxy_1080p": ROIS[roi_name],
                "score_floor": floor,
                "body_proposal_count": sum(
                    p["score"] >= floor for r in samples for p in r["peaks"][roi_name]
                ),
                "yellow_handle_supported_count": sum(len(r["body_proposals"]) for r in rows),
                "path_direction_counts": dict(Counter(p["direction"] for p in paths)),
                "image_motion_paths": paths,
                "supported_samples": [r for r in rows if r["body_proposals"]],
            }
    frozen = variants["frozen_score_0.55"]
    baseline_paths = baseline["image_motion_paths"]["yellow"]
    if (
        frozen["body_proposal_count"] != baseline["proposal_counts"]["yellow"]["body"]
        or frozen["yellow_handle_supported_count"]
        != baseline["proposal_counts"]["yellow"]["handle_supported"]
        or frozen["image_motion_paths"] != baseline_paths
    ):
        raise AssertionError("Frozen variant does not reproduce baseline")
    result = {
        "status": "postreview_development_ablation_not_independent_validation",
        "source_match": "Canada–Korea 2024",
        "source_interval_s": [START_S, STOP_S],
        "sample_period_s": 1,
        "target_video_sha256": digest(VIDEO),
        "latvia_template_video_sha256": digest(LATVIA),
        "baseline_audit_sha256": digest(BASELINE),
        "runner_sha256": digest(Path(__file__)),
        "body_code_sha256": digest(ROOT / "prototype/scripts/probe_latvia_1080p_body_paths.py"),
        "handle_code_sha256": digest(ROOT / "prototype/scripts/screen_latvia_body_with_handle.py"),
        "frozen_baseline_reproduced": True,
        "handle_min_yellow_pixels": 120,
        "variants": variants,
        "limitations": [
            "Score and ROI variants were chosen after inspecting T11; this is development data.",
            "Paths are linked image proposals, not event truth or persistent stone identities.",
            "One-second sampling cannot measure exact release, stop or spin.",
            "Source review is required for any added paths before claiming actual throws.",
        ],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(
        json.dumps(
            {
                key: {
                    k: v[k]
                    for k in (
                        "body_proposal_count",
                        "yellow_handle_supported_count",
                        "path_direction_counts",
                    )
                }
                for key, v in variants.items()
            }
        )
    )


if __name__ == "__main__":
    main()
