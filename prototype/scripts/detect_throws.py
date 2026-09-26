"""Process a continuous source interval. Inference never loads reference annotations."""

import sys, json, time, argparse, hashlib
from pathlib import Path
import cv2
from dataclasses import asdict

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from throw_detection import PassageDetector, VERSION

p = argparse.ArgumentParser()
p.add_argument("--start", type=float, default=1650)
p.add_argument("--end", type=float, default=2760)
p.add_argument("--output", default="predictions.json")
args = p.parse_args()
cap = cv2.VideoCapture(str(ROOT / "sources/canada-korea-2024-360p.mp4"))
fps = cap.get(cv2.CAP_PROP_FPS)
step = round(fps / 10)
startframe = round(args.start * fps)
cap.set(cv2.CAP_PROP_POS_FRAMES, startframe)
det = PassageDetector()
samples = 0
start = time.monotonic()
records = []
for n in range(startframe, round(args.end * fps)):
    ok = cap.grab()
    if not ok:
        raise RuntimeError(f"Decode failed at {n / fps}")
    if (n - startframe) % step:
        continue
    ok, frame = cap.retrieve()
    if not ok:
        raise RuntimeError("Retrieval failed")
    t = n / fps
    from throw_detection import stone_candidates

    candidates = stone_candidates(frame, det.config)
    events = det.update(candidates, t)
    samples += 1
    for e in events:
        print(e, flush=True)
    if samples % 2000 == 0:
        print("samples", samples, flush=True)
cap.release()
paths = det.trajectories()
for e in det.events:
    e["trajectory"] = paths.get(e["track_id"], [])
result = {
    "version": VERSION,
    "model_sha256": hashlib.sha256((ROOT / "throw_detection.py").read_bytes()).hexdigest(),
    "source": "aWXo6XeUFQw",
    "source_interval_s": [args.start, args.end],
    "view": "left",
    "processing_size": [640, 360],
    "samples": samples,
    "sample_rate_hz": fps / step,
    "config": asdict(det.config),
    "processing_seconds": time.monotonic() - start,
    "events": det.events,
    "limitations": [
        "Fixed-view outgoing passage detector, not exact release recognition.",
        "No automatic layout or end direction discovery.",
        "Stone colour does not identify a player.",
        "No intended destination or success score inferred.",
    ],
}
(ROOT / "throw-analysis" / args.output).write_text(json.dumps(result, indent=2))
print("EVENTS", len(det.events), "seconds", result["processing_seconds"])
