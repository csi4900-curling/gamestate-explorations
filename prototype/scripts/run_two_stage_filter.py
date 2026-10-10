"""Apply one 2024 image-context confirmation policy to raw throw proposals.

Supports both virtual-line and line-independent 2024 proposal artifacts. Every
proposal remains in the output ledger even if the gate does not confirm it.
This is a development policy for the known split-screen layout, not a general
physical-release detector.
"""

import argparse
import json
import sys
from pathlib import Path

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cache_contract import file_sha256
from passage_motion_context import motion_context_features
from span_context_confirmation import confirm_span_context
from two_stage_throw_triage import triage_candidates


def passage_y(event):
    y = event.get("passage_y_px")
    if y is None:
        y = event.get("gate_y_px")
    if y is None:
        raise ValueError(f"Candidate lacks an observed passage y-coordinate: {event['id']}")
    return y


def measure_candidates(video, events):
    cap = cv2.VideoCapture(str(video), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0:
        raise ValueError("Unreadable video")

    def frame_at(t):
        cap.set(cv2.CAP_PROP_POS_FRAMES, round(t * fps))
        ok, frame = cap.read()
        if not ok:
            raise RuntimeError(f"Cannot decode source frame at {t:.3f} s")
        return frame

    rows = []
    try:
        for event in events:
            t = event["crossing_time_s"]
            x, y = event["crossing_x_px"], passage_y(event)
            rows.append({
                "id": event["id"], "time_s": t, "x_px": x, "y_px": y,
                **motion_context_features(frame_at(t - 0.25), frame_at(t + 0.25), x=x, y=y),
            })
    finally:
        cap.release()
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--candidates", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists; preserve previous results")
    source = json.loads(args.candidates.read_text())
    configs = source.get("config")
    configs = configs if isinstance(configs, list) else [configs]
    if not configs or any(not isinstance(config, dict) or config.get("roi") != [40, 4, 280, 116]
                          for config in configs):
        parser.error("Only the known 2024 split-screen departure ROI is supported")
    digest = file_sha256(args.video)
    if digest != source["source_sha256"]:
        parser.error("Video fingerprint does not match candidates")
    reserved = json.loads((ROOT / "validation/unseen-end/reservation.json").read_text())
    if (digest == reserved["source_sha256"] or
            args.video.resolve() == (ROOT / "validation/unseen-end/source.mp4").resolve() or
            any(source["source_id"] in row["video_url"] for row in reserved["reserved_rows"])):
        parser.error("This source is reserved for independent evaluation")
    rows = measure_candidates(args.video, source["events"])
    decisions = confirm_span_context(source["events"], rows)
    accepted = {row["id"] for row in decisions if row["status"] == "confirmed"}
    stage = {
        "events": [event for event in source["events"] if event["id"] in accepted],
        "withheld_events": [event for event in source["events"] if event["id"] not in accepted],
        "decisions": decisions,
    }
    triaged = triage_candidates(source["events"], [("image_context", stage)])
    result = {
        "status": "development_split_2024_two_stage_filter",
        "source_id": source["source_id"],
        "source_sha256": digest,
        "source_interval_s": source["source_interval_s"],
        "proposal_sha256": file_sha256(args.candidates),
        "video_motion_code_sha256": file_sha256(ROOT / "prototype/passage_motion_context.py"),
        "gate_code_sha256": file_sha256(ROOT / "prototype/span_context_confirmation.py"),
        "triage_code_sha256": file_sha256(ROOT / "prototype/two_stage_throw_triage.py"),
        "runner_sha256": file_sha256(__file__),
        "motion_rows": rows,
        "decisions": decisions,
        "events": stage["events"],
        "review_events": stage["withheld_events"],
        "proposals": triaged["proposals"],
        "counts": triaged["counts"],
        "limitations": [
            "The context gate was developed on exposed 2024 recordings; reuse on those sources is post-score development.",
            "The fixed 2024 split-screen departure ROI is required; other layouts are unsupported.",
            "Withheld proposals remain review candidates, not proven non-throws.",
            "Observed passage times are not exact physical release times.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps(result["counts"]))


if __name__ == "__main__":
    main()
