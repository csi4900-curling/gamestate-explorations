"""Re-detect cap centres at native resolution on known departure-track timestamps.
Uses each frame's left calibration, never the receiving homography.
"""

from pathlib import Path
import argparse, sys, json, time
import cv2, numpy as np

cv2.setNumThreads(2)
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from vision_core import ViewCalibrator
from body_localization import detect_and_localize, transported_reference_camera
from cache_contract import context_for, read_cache, write_cache

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--output", type=Path, default=ROOT / "cross-view")
parser.add_argument(
    "--force", action="store_true", help="Recompute instead of reusing cached observations"
)
parser.add_argument("--limit", type=int, help="Process only the first N events, for smoke checks")
args = parser.parse_args()
if args.limit is not None and args.limit < 1:
    parser.error("--limit must be positive")
cache_context = context_for(
    [
        ROOT / "throw-analysis/end3.mp4",
        ROOT / "throw-analysis/predictions.json",
        ROOT / "vision/annotations/calibration.json",
        ROOT / "vision/frames/00750.jpg",
        ROOT / "vision/frames/06495.jpg",
        ROOT / "rectification/calibration.json",
        ROOT / "body_localization.py",
        ROOT / "vision_core.py",
        ROOT / "continuous_tracker.py",
        ROOT / "target_analysis.py",
        ROOT / "cache_contract.py",
        Path(__file__),
    ],
    {
        "source_start_s": 1650,
        "source_end_s": 2760,
        "opencv": cv2.__version__,
        "numpy": np.__version__,
    },
)
out = args.output
out.mkdir(parents=True, exist_ok=True)
events = json.loads((ROOT / "throw-analysis/predictions.json").read_text())["events"]
cfg = json.loads((ROOT / "vision/annotations/calibration.json").read_text())["views"]["left"]
cfg = dict(cfg, world_bounds=[-2.375, -18.0, 2.375, 1.975])
cal = ViewCalibrator(cfg, ROOT / "vision/frames")
cal.H = np.array(
    json.loads((ROOT / "rectification/calibration.json").read_text())["left"]["refined_H"]
)
cap = cv2.VideoCapture(str(ROOT / "throw-analysis/end3.mp4"))
fps = cap.get(cv2.CAP_PROP_FPS)
started = time.monotonic()
if not cap.isOpened() or not np.isfinite(fps) or fps <= 0:
    raise ValueError("Cannot open source video or read its frame rate")
for e in events[: args.limit]:
    dest = out / (e["id"] + "-departure.json")
    event_context = dict(cache_context, event_id=e["id"])
    points = e["trajectory"]
    saved = read_cache(dest, event_context, args.force)
    existing = saved["records"] if saved is not None else []
    cached = {r["time_s"]: r for r in existing}
    if len(cached) == len(points):
        continue
    records = []
    first = round((points[0]["time_s"] - 1650) * fps)
    cap.set(cv2.CAP_PROP_POS_FRAMES, first)
    frame_index = first
    for p in points:
        if p["time_s"] in cached:
            records.append(cached[p["time_s"]])
            continue
        target = round((p["time_s"] - 1650) * fps)
        while frame_index < target:
            if not cap.grab():
                raise RuntimeError("Decode failed")
            frame_index += 1
        ok, f = cap.read()
        frame_index += 1
        if not ok:
            raise RuntimeError(target)
        H, reg = cal.register(f)
        seed = np.array(p["pixel"]) * 3
        row = {
            "time_s": p["time_s"],
            "seed_pixel": seed.tolist(),
            "H": H.tolist() if H is not None else None,
            "registration": reg,
            "position_local_m": None,
            "pixel": None,
            "status": "geometry_unavailable",
        }
        if H is not None:
            ref = cv2.warpPerspective(
                cal.reference, np.array(reg["reference_to_current"]), (1920, 1080)
            )
            prior = transported_reference_camera(cal.H, H, cfg["region"])
            ds, _ = detect_and_localize(f, H, cfg, ref, prior)
            nearby = [
                d
                for d in ds
                if d["colour"] == e["colour"]
                and np.linalg.norm(np.array(d["pixel_center"]) - seed) <= max(12, p["bbox"][2] * 3)
            ]
            row["candidate_count"] = len(nearby)
            row["status"] = "cap_association_ambiguous_or_missing"
            if len(nearby) == 1:
                d = nearby[0]
                row.update(
                    position_local_m=d["ground_position_m"],
                    pixel=d["pixel_center"],
                    localization=d["localization"],
                    status="conditional_cap_position"
                    if d["ground_position_m"] is not None
                    else "position_unavailable",
                )
        records.append(row)
    write_cache(
        dest,
        {
            "event_id": e["id"],
            "expanded_departure_bounds_m": cfg["world_bounds"],
            "records": records,
            "claim": "Conditional positions outside the house calibration footprint; no independent metric validation here.",
        },
        event_context,
    )
    print(
        e["id"],
        sum(r["position_local_m"] is not None for r in records),
        "/",
        len(records),
        "elapsed",
        round(time.monotonic() - started),
        flush=True,
    )
cap.release()
