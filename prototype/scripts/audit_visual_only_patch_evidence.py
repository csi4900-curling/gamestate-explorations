"""Score source-video cap tracks for every visual-only ledger proposal."""

import argparse
from collections import Counter
import json
from pathlib import Path
import sys

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cache_contract import file_sha256  # noqa: E402
from cap_patch_verifier import score_candidates  # noqa: E402
from stone_motion_fallback import moving_cap_tracks, stone_cap_candidates  # noqa: E402
from stone_patch_detector import load_model  # noqa: E402
from visual_only_patch_evidence import (patch_evidence_status,  # noqa: E402
                                        summarize_tracks)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", required=True, type=Path)
    parser.add_argument("--ledger", required=True, type=Path)
    parser.add_argument("--model", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Patch evidence artifact already exists")
    ledger = json.loads(args.ledger.read_text())
    source_hash = file_sha256(args.video)
    if ledger["source_sha256"] != source_hash:
        parser.error("Source hash mismatch")
    reserved = json.loads((ROOT / "validation/unseen-end/reservation.json").read_text())
    if source_hash == reserved["source_sha256"]:
        parser.error("Reserved source cannot be used for development audit")
    model = load_model(args.model)
    cap = cv2.VideoCapture(str(args.video), cv2.CAP_FFMPEG,
                           [cv2.CAP_PROP_N_THREADS, 1])
    if not cap.isOpened():
        parser.error("Cannot open source video")
    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0:
        parser.error("Invalid source frame rate")
    rows = []
    try:
        for event in ledger["events"]:
            if event["counter_id"] is not None:
                continue
            start, end = event["release_window_s"]
            if not start < end:
                parser.error("Invalid candidate window")
            colours = [event["colour"]] if event["colour"] else ["red", "yellow"]
            observations = {colour: [] for colour in colours}
            for tick in range(round(start * 5), round(end * 5)):
                time_s = round(tick / 5, 3)
                cap.set(cv2.CAP_PROP_POS_FRAMES, round(time_s * fps))
                ok, frame = cap.read()
                if not ok:
                    raise RuntimeError(f"Frame decode failed at {time_s}")
                for colour in colours:
                    proposals = stone_cap_candidates(frame, colour,
                                                     allow_bright_body=True,
                                                     allow_large_caps=True)
                    observations[colour].append((time_s, score_candidates(
                        frame, proposals, model)))
            tracks = [(colour, track) for colour, samples in observations.items()
                      for track in moving_cap_tracks(samples, max_gap_s=1.6,
                                                     max_step_px=130)]
            summary = summarize_tracks(tracks, float(model["threshold"]))
            rows.append({
                "candidate_id": event["candidate_id"],
                "camera_shot_id": event["shot_id"],
                "release_window_s": event["release_window_s"],
                "candidate_colour": event["colour"],
                "evidence_sources": event["evidence_sources"],
                "patch_evidence_status": patch_evidence_status(summary),
                "tracks": summary,
            })
    finally:
        cap.release()
    counts = Counter(row["patch_evidence_status"] for row in rows)
    result = {
        "status": "development_visual_only_patch_diagnostic_not_event_filter",
        "source_sha256": source_hash,
        "source_interval_s": ledger["source_interval_s"],
        "ledger_sha256": file_sha256(args.ledger),
        "model_sha256": file_sha256(args.model),
        "cap_code_sha256": file_sha256(ROOT / "prototype/stone_motion_fallback.py"),
        "patch_code_sha256": file_sha256(ROOT / "prototype/cap_patch_verifier.py"),
        "summary_code_sha256": file_sha256(ROOT / "prototype/visual_only_patch_evidence.py"),
        "runner_sha256": file_sha256(__file__),
        "sample_rate_hz": 5,
        "visual_only_candidate_count": len(rows),
        "counts": dict(counts),
        "rows": rows,
        "limitations": [
            "The patch model was trained on exposed development imagery, not independent event labels.",
            "Stone-like appearance does not prove delivery, and its absence does not disprove an off-camera throw.",
            "A cap track can follow people, graphics, old stones or camera motion.",
            "This audit preserves all candidates and makes no final throw decision.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print({"visual_only": len(rows), **counts})


if __name__ == "__main__":
    main()
