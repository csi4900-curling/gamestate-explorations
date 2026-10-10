"""Attach full-recording layout support to right-entry review proposals."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
sys.path.insert(0, str(ROOT / "prototype/scripts"))
from layout_preflight import frame_evidence
from run_throw_pipeline import sample_layout


def digest(path):
    h = sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--right", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists")
    right = json.loads(args.right.read_text())
    video_hash = digest(args.video)
    if video_hash != right["source_sha256"]:
        parser.error("Source fingerprints differ")
    start, stop = right["source_interval_s"]
    route, samples, duration = sample_layout(args.video, start, stop, chunk_s=90)
    cap = cv2.VideoCapture(str(args.video), cv2.CAP_FFMPEG,
                           [cv2.CAP_PROP_N_THREADS, 1])
    if not cap.isOpened():
        parser.error("Unreadable video")
    fps = cap.get(cv2.CAP_PROP_FPS)
    rows = []
    try:
        for entry in right["entry_review_proposals"]:
            t = entry["entry_crossing"]["time_s"]
            run = next((r for r in route["runs"]
                        if r["interval_s"][0] <= t < r["interval_s"][1]), None)
            if run is None:
                raise ValueError(f"No layout run covers entry {t}")
            cap.set(cv2.CAP_PROP_POS_FRAMES, round(t * fps))
            ok, frame = cap.read()
            if not ok:
                raise RuntimeError(f"Cannot decode entry frame {t}")
            evidence = frame_evidence(frame)
            rows.append({"right_raw_track_id": entry["raw_track_id"],
                         "entry_time_s": t, "colour_claim": entry["colour_claim"],
                         "preflight_run_layout": run["layout"],
                         "preflight_run_interval_s": run["interval_s"],
                         "entry_frame_split_2024_signature": evidence["split_2024_signature"],
                         "entry_frame_evidence": evidence})
    finally:
        cap.release()
    result = {
        "status": "right_entry_layout_coverage_audit_not_throw_validation",
        "source_sha256": video_hash,
        "right_sha256": digest(args.right),
        "layout_code_sha256": digest(ROOT / "prototype/layout_preflight.py"),
        "layout_runner_sha256": digest(ROOT / "prototype/scripts/run_throw_pipeline.py"),
        "runner_sha256": digest(Path(__file__)),
        "source_interval_s": [start, stop],
        "source_duration_s": duration,
        "preflight_sample_period_s": 10,
        "preflight_chunk_s": 90,
        "route": route,
        "preflight_samples": samples,
        "entry_layout_audit": rows,
        "limitations": [
            "A 90-second layout run can contain shorter camera cuts or frozen panels.",
            "A split signature at entry is image geometry, not proof of a physical throw.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"entries": len(rows), "route": route["layout"],
                      "supported_entry_count": sum(r["preflight_run_layout"] ==
                                                   "split_2024" and
                                                   r["entry_frame_split_2024_signature"]
                                                   for r in rows)}))


if __name__ == "__main__":
    main()
