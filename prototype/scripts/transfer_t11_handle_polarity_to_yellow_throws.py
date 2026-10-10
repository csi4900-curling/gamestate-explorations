"""Apply T11's frozen two-pose handle cue to every other yellow throw in end 3."""

from hashlib import sha256
import json
from pathlib import Path
import sys

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype/scripts"))
from probe_t11_handle_periodicity import normalized_yellow_mask, mask_series  # noqa: E402
from probe_t11_handle_polarity import (TEMPLATE_LEFT_S, TEMPLATE_RIGHT_S,
                                       polarity)  # noqa: E402

VIDEO = ROOT / "prototype/throw-analysis/end3.mp4"
SOURCE_META = ROOT / "prototype/throw-analysis/source.json"
CROSS_VIEW = ROOT / "prototype/cross-view/results.json"
T11_PILOT = ROOT / "validation/spin-observability/T11-handle-polarity-pilot.json"
OUTPUT = ROOT / "validation/spin-observability/T11-template-yellow-transfer.json"


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def component_quality(frame, x, y):
    patch = frame[y - 40:y + 8, x - 40:x + 40]
    if patch.shape[:2] != (48, 80):
        return {"crop_in_frame": False, "yellow_component_at_crop_edge": None,
                "yellow_component_width_px": None}
    hsv = cv2.cvtColor(patch, cv2.COLOR_BGR2HSV)
    mask = (((hsv[:, :, 0] > 16) & (hsv[:, :, 0] < 42) &
             (hsv[:, :, 1] > 65) & (hsv[:, :, 2] > 75))).astype(np.uint8)
    count, labels, stats, _ = cv2.connectedComponentsWithStats(mask)
    if count < 2:
        return {"crop_in_frame": True, "yellow_component_at_crop_edge": None,
                "yellow_component_width_px": None}
    component = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    xx = np.where(labels == component)[1]
    return {"crop_in_frame": True,
            "yellow_component_at_crop_edge": bool(xx.min() <= 2 or xx.max() >= 77),
            "yellow_component_width_px": int(xx.max() - xx.min() + 1)}


def main():
    if OUTPUT.exists():
        raise SystemExit("T11-template transfer already exists")
    pilot = json.loads(T11_PILOT.read_text())
    meta = json.loads(SOURCE_META.read_text())
    data = json.loads(CROSS_VIEW.read_text())
    if (digest(VIDEO) != pilot["source_video_sha256"] or
            digest(CROSS_VIEW) != pilot["cross_view_results_sha256"] or
            tuple(pilot["template_left_times_s"]) != TEMPLATE_LEFT_S or
            tuple(pilot["template_right_times_s"]) != TEMPLATE_RIGHT_S):
        raise ValueError("Frozen T11 template inputs differ")
    cap = cv2.VideoCapture(str(VIDEO), cv2.CAP_FFMPEG,
                           [cv2.CAP_PROP_N_THREADS, 1])
    if not cap.isOpened():
        raise RuntimeError("Cannot open source video")
    rows = []
    try:
        t11 = next(row for row in data["throws"] if row["id"] == "T11")
        template_times = np.round(np.arange(2307.0, 2312.51, 0.1), 3)
        masks, retained = mask_series(cap, t11, template_times,
                                      meta["source_interval_s"][0])
        if len(retained) != len(template_times):
            raise RuntimeError("T11 template masks missing")
        by_time = {t: i for i, t in enumerate(retained)}
        left = np.mean(masks[[by_time[t] for t in TEMPLATE_LEFT_S]], axis=0)
        right = np.mean(masks[[by_time[t] for t in TEMPLATE_RIGHT_S]], axis=0)
        selected = [row for row in data["throws"] if row["colour"] == "yellow"
                    and row["id"] != "T11"]
        for throw in selected:
            points = throw["arrival"]
            start = points[0]["time_s"]
            end = min(start + 5.0, points[-1]["time_s"])
            times = np.round(np.arange(start, end + 0.001, 0.2), 3)
            pt = np.array([point["time_s"] for point in points])
            xp = np.array([point["pixel"][0] for point in points])
            yp = np.array([point["pixel"][1] for point in points])
            samples = []
            for t in times:
                x = int(round(np.interp(t, pt, xp)))
                y = int(round(np.interp(t, pt, yp)))
                cap.set(cv2.CAP_PROP_POS_MSEC,
                        (t - meta["source_interval_s"][0]) * 1000)
                ok, frame = cap.read()
                if not ok:
                    raise RuntimeError(f"Frame decode failed at {t}")
                quality = component_quality(frame, x, y)
                mask = normalized_yellow_mask(frame, x, y)
                samples.append({"time_s": float(t), "track_pixel": [x, y],
                                **quality,
                                "polarity": polarity(mask, left, right)
                                if mask is not None else None})
            good = [sample for sample in samples if sample["polarity"] is not None
                    and sample["yellow_component_at_crop_edge"] is False]
            rows.append({"throw_id": throw["id"],
                         "arrival_interval_s": [points[0]["time_s"],
                                                points[-1]["time_s"]],
                         "sample_count": len(samples),
                         "unclipped_polarity_count": len(good),
                         "edge_clipped_count": sum(
                             sample["yellow_component_at_crop_edge"] is True
                             for sample in samples),
                         "unclipped_polarity_range": [
                             round(min(s["polarity"] for s in good), 5),
                             round(max(s["polarity"] for s in good), 5)] if good else None,
                         "samples": samples})
            print(throw["id"], len(good), "unclipped", flush=True)
    finally:
        cap.release()
    result = {
        "status": "development_same_recording_t11_pose_template_transfer_not_spin_count",
        "source_video_sha256": digest(VIDEO),
        "cross_view_results_sha256": digest(CROSS_VIEW),
        "t11_pilot_sha256": digest(T11_PILOT),
        "mask_extraction_code_sha256": digest(ROOT / "prototype/scripts/probe_t11_handle_periodicity.py"),
        "polarity_code_sha256": digest(ROOT / "prototype/scripts/probe_t11_handle_polarity.py"),
        "runner_sha256": digest(Path(__file__)),
        "selection": "all seven other yellow throws in cross-view end-three ledger",
        "sample_rate_hz": 5,
        "rows": rows,
        "limitations": [
            "The T11 templates were selected after inspecting T11, and all throws share the same source recording.",
            "Trajectory centers are provisional and can crop a handle at the edge; edge flag does not catch every localization error.",
            "Polarity variation alone is not a validated left/right pose label or a revolution count.",
            "No camera handoff, physical event identity or full-throw spin count is verified.",
        ],
    }
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
