"""Process every detected passage's receiving window without reading evaluation labels."""

from pathlib import Path
import argparse, sys, json, time, hashlib
import cv2, numpy as np

cv2.setNumThreads(2)
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from vision_core import ViewCalibrator
from body_localization import detect_and_localize, transported_reference_camera
from continuous_tracker import Tracker
from target_analysis import receiving_outcome
from cache_contract import context_for, read_cache, write_cache

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--output", type=Path, default=ROOT / "throw-segments")
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
cfg = json.loads((ROOT / "vision/annotations/calibration.json").read_text())["views"]["right"]
cal = ViewCalibrator(cfg, ROOT / "vision/frames")
cal.H = np.array(
    json.loads((ROOT / "rectification/calibration.json").read_text())["right"]["refined_H"]
)
cap = cv2.VideoCapture(str(ROOT / "throw-analysis/end3.mp4"))
fps = cap.get(cv2.CAP_PROP_FPS)
started = time.monotonic()
if not cap.isOpened() or not np.isfinite(fps) or fps <= 0:
    raise ValueError("Cannot open source video or read its frame rate")
segments = []
for i, event in enumerate(events[: args.limit]):
    dest = out / (event["id"] + ".json")
    event_context = dict(cache_context, event_id=event["id"])
    saved = read_cache(dest, event_context, args.force)
    if saved is not None:
        segments.append(saved)
        continue
    start = event["crossing_time_s"]
    boundary = events[i + 1]["crossing_time_s"] if i + 1 < len(events) else 2760.0
    # Include pre-arrival baseline, then up to 45 seconds after gate passage.
    first = np.floor((start - 3) * 2) / 2
    last = min(boundary - 0.5, start + 45)
    tracker = Tracker()
    records = []
    frame_index = round((first - 1650) * fps)
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
    for t in np.arange(first, last + 0.001, 0.5):
        target_frame = round((t - 1650) * fps)
        while frame_index < target_frame:
            if not cap.grab():
                raise RuntimeError("Decode ended early")
            frame_index += 1
        ok, frame = cap.read()
        frame_index += 1
        if not ok:
            raise RuntimeError(f"Decode failed at {t}")
        H, reg = cal.register(frame)
        reference = None
        prior = None
        if H is not None:
            reference = cv2.warpPerspective(
                cal.reference, np.array(reg["reference_to_current"]), (1920, 1080)
            )
            prior = transported_reference_camera(cal.H, H, cfg["region"])
        stones, detail = detect_and_localize(frame, H, cfg, reference, prior)
        records.append(
            {
                "time_s": float(t - first),
                "source_time_s": float(t),
                "views": {
                    "right": {
                        "stones": tracker.update(stones, float(t)),
                        "registration": reg,
                        "H": H.tolist() if H is not None else None,
                    }
                },
            }
        )
    timeline = {"source_start_s": float(first), "records": records}
    outcome = receiving_outcome(timeline, event)
    result = {
        "event": event,
        "review_interval_s": [start, boundary],
        "receiving_analysis_interval_s": [float(first), float(last)],
        "outcome": outcome,
        "timeline": timeline,
        "calibration_accepted_samples": sum(r["views"]["right"]["H"] is not None for r in records),
        "analysis_sample_count": len(records),
        "limitations": [
            "Next passage is a review boundary, not physical throw completion.",
            "Receiving association is a same-colour motion heuristic, not cross-camera identity proof.",
            "Settling applies only to the associated stone; other stones may still move.",
            "Receiving analysis stops at 45 seconds after passage or before the next passage.",
            "No straight-line reconstruction before the gate.",
        ],
    }
    write_cache(dest, result, event_context)
    segments.append(result)
    print(
        event["id"],
        outcome["status"],
        "settled",
        outcome.get("settled", {}),
        "registration",
        result["calibration_accepted_samples"],
        "/",
        len(records),
        "elapsed",
        round(time.monotonic() - started),
        flush=True,
    )
cap.release()
(out / "manifest.json").write_text(
    json.dumps(
        {
            "source_start_s": 1650,
            "source_end_s": 2760,
            "segments": [
                {
                    "id": s["event"]["id"],
                    "file": s["event"]["id"] + ".json",
                    "review_interval_s": s["review_interval_s"],
                    "outcome_status": s["outcome"]["status"],
                }
                for s in segments
            ],
            "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "detector_sha256": hashlib.sha256(
                (ROOT / "body_localization.py").read_bytes()
            ).hexdigest(),
            "processing_seconds": time.monotonic() - started,
        },
        indent=2,
    )
)
