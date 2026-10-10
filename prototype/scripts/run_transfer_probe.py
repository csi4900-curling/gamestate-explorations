"""Run the frozen passage detector on an explicitly separate exploratory recording."""

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys
import time
import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cache_contract import file_sha256
from throw_detection import PassageDetector, stone_candidates, VERSION


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--video", type=Path, required=True)
    p.add_argument("--source-id", required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--start", type=float, default=1650)
    p.add_argument("--end", type=float, default=2760)
    a = p.parse_args()
    reserved = json.loads((ROOT / "validation/unseen-end/reservation.json").read_text())
    if any(a.source_id in row["video_url"] for row in reserved["reserved_rows"]):
        p.error("This event is reserved for independent evaluation")
    if a.video.resolve() == (ROOT / "validation/unseen-end/source.mp4").resolve():
        p.error("Reserved media must not be processed")
    digest = file_sha256(a.video)
    if digest == reserved["source_sha256"]:
        p.error("This is a copy of the reserved media")
    a.output.mkdir(parents=True, exist_ok=False)
    cv2.setNumThreads(1)
    detector = PassageDetector()
    cap = cv2.VideoCapture(str(a.video), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    fps = cap.get(cv2.CAP_PROP_FPS)
    duration = cap.get(cv2.CAP_PROP_FRAME_COUNT) / fps if fps > 0 else 0
    if not 0 <= a.start < a.end <= duration:
        raise ValueError("Invalid interval or unreadable video")
    manifest = {
        "status": "exploratory_not_independent_validation",
        "source_id": a.source_id,
        "source_sha256": digest,
        "source_interval_s": [a.start, a.end],
        "selection": "Fixed elapsed-time interval matching the historical run; not selected by detections and not asserted to be a complete end.",
        "model_sha256": file_sha256(ROOT / "prototype/throw_detection.py"),
        "runner_sha256": file_sha256(__file__),
        "version": VERSION,
        "config": asdict(detector.config),
        "opencv": cv2.__version__,
        "frozen_before_inference": True,
    }
    (a.output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    start = time.monotonic()
    step = max(1, round(fps / 10))
    first = round(a.start * fps)
    cap.set(cv2.CAP_PROP_POS_FRAMES, first)
    samples = 0
    proposals = 0
    for n in range(first, round(a.end * fps)):
        if not cap.grab():
            raise RuntimeError(f"Decode failed at {n / fps}")
        if (n - first) % step:
            continue
        ok, frame = cap.retrieve()
        if not ok:
            raise RuntimeError("Frame retrieval failed")
        candidates = stone_candidates(frame, detector.config)
        proposals += len(candidates)
        detector.update(candidates, n / fps)
        samples += 1
        if samples % 1500 == 0:
            print(f"{samples} samples, {len(detector.events)} provisional events", flush=True)
    cap.release()
    paths = detector.trajectories()
    events = [dict(e, trajectory=paths[e["track_id"]]) for e in detector.events]
    result = dict(
        manifest,
        events=events,
        samples=samples,
        proposals=proposals,
        sample_rate_hz=fps / step,
        processing_seconds=time.monotonic() - start,
        accuracy=None,
        reference_events=None,
        limitations=[
            "No independent event labels: no measured precision or recall.",
            "Fixed old camera region, direction and gate; no source-specific retuning.",
            "No full board, release, physical trajectory or cross-view identity accuracy claim.",
        ],
    )
    (a.output / "results.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"events": len(events), "samples": samples, "proposals": proposals}))


if __name__ == "__main__":
    main()
