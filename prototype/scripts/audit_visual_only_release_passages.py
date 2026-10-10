"""Scan visual-only windows for held-stone-to-motion release cues."""

import argparse
from collections import Counter
import json
from pathlib import Path
import sys

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from prototype.cache_contract import file_sha256  # noqa: E402
from prototype.origin_release_passage import scan_origin_release  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Release-passage audit already exists")
    ledger = json.loads(args.ledger.read_text())
    source_hash = file_sha256(args.video)
    if ledger["source_sha256"] != source_hash:
        parser.error("Source hash mismatch")
    reserved = json.loads((ROOT / "validation/unseen-end/reservation.json").read_text())
    if source_hash == reserved["source_sha256"]:
        parser.error("Reserved source cannot be used for development audit")
    cap = cv2.VideoCapture(str(args.video), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    if not cap.isOpened():
        parser.error("Cannot open source video")
    fps = cap.get(cv2.CAP_PROP_FPS)
    rows = []
    try:
        for event in ledger["events"]:
            if event["counter_id"] is not None:
                continue
            start, end = event["release_window_s"]
            if not start < end:
                parser.error("Invalid candidate window")
            result = scan_origin_release(cap, fps, start, end)
            cues = result["passages"]
            matching = [
                cue for cue in cues if event["colour"] is None or cue["colour"] == event["colour"]
            ]
            rows.append(
                {
                    "candidate_id": event["candidate_id"],
                    "camera_shot_id": event["shot_id"],
                    "release_window_s": event["release_window_s"],
                    "candidate_colour": event["colour"],
                    "filtered_cap_observation_count": result["filtered_cap_observation_count"],
                    "passages": cues,
                    "colour_compatible_passage_count": len(matching),
                    "status": (
                        "unique_colour_compatible_passage"
                        if len(matching) == 1 and len(cues) == 1
                        else "no_colour_compatible_passage"
                        if not matching
                        else "ambiguous_passages"
                    ),
                }
            )
    finally:
        cap.release()
    counts = Counter(row["status"] for row in rows)
    result = {
        "status": "development_visual_only_release_cue_diagnostic_not_event_filter",
        "source_sha256": source_hash,
        "source_interval_s": ledger["source_interval_s"],
        "ledger_sha256": file_sha256(args.ledger),
        "release_code_sha256": file_sha256(ROOT / "prototype/origin_release_passage.py"),
        "runner_sha256": file_sha256(__file__),
        "visual_only_candidate_count": len(rows),
        "counts": dict(counts),
        "rows": rows,
        "limitations": [
            "The scanner assumes a Beijing-style delivery-side lower-ice region.",
            "A real release can occur off camera or fail the held-cap track; no passage is not a negative label.",
            "A passage cue does not prove distinct physical identity or exact release time.",
            "The audit preserves all candidate events and makes no final acceptance decision.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print({"visual_only": len(rows), **counts})


if __name__ == "__main__":
    main()
