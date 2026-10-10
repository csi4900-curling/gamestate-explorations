"""Score a frozen event file against a separately prepared reference file."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "prototype"))
from throw_event_benchmark import evaluate_events
from event_acceptance import assess_recording


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def video_duration_s(path):
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True, check=True,
    )
    return float(probe.stdout.strip())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", required=True, type=Path)
    parser.add_argument("--predictions", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--tolerance-s", type=float, default=0.0)
    parser.add_argument(
        "--prediction-time-mode", choices=("point", "evidence_interval"), default="point"
    )
    parser.add_argument("--max-prediction-interval-s", type=float)
    parser.add_argument("--source-video", type=Path,
                        help="Actual complete source recording; required with --assess-target")
    parser.add_argument(
        "--assess-target",
        action="store_true",
        help="Also apply the strict full-source 0.95 precision/recall gate",
    )
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists; preserve earlier scores")
    ref = json.loads(args.reference.read_text())
    pred = json.loads(args.predictions.read_text())
    if ref.get("source_id") != pred.get("source_id"):
        parser.error("Source IDs differ")
    if ref.get("source_interval_s") != pred.get("source_interval_s"):
        parser.error("Source intervals differ")
    if ref.get("source_sha256") and pred.get("source_sha256") != ref["source_sha256"]:
        parser.error("Source fingerprints differ")
    if ref.get("reference_method") not in (
        "human_independent",
        "agent_blind",
        "ai_retrospective",
        "publisher_labels",
        "publisher_independent",
    ):
        parser.error("Reference method must be explicit")
    if args.assess_target and (args.tolerance_s != 0 or args.prediction_time_mode != "point"):
        parser.error("Target assessment requires zero tolerance and point timestamps")
    if args.assess_target and (args.source_video is None or not args.source_video.is_file()):
        parser.error("Target assessment requires --source-video pointing to the complete source file")
    if "events" not in pred and not args.assess_target:
        parser.error("Predictions lack exhaustive events; use --assess-target for coverage audit")
    score = (
        evaluate_events(
            pred["events"],
            ref["events"],
            ref["source_interval_s"],
            tolerance_s=args.tolerance_s,
            prediction_time_mode=args.prediction_time_mode,
            max_prediction_interval_s=args.max_prediction_interval_s,
        )
        if "events" in pred
        else None
    )
    result = {
        "source_id": ref["source_id"],
        "reference_method": ref["reference_method"],
        "source_interval_s": ref["source_interval_s"],
        "reference_sha256": sha(args.reference),
        "predictions_sha256": sha(args.predictions),
        "scorer_sha256": sha(ROOT / "prototype/throw_event_benchmark.py"),
        "score": score,
        "limits": [
            "An F1 score inherits the completeness and independence limits of its reference.",
            "One-to-one interval agreement is not release-time accuracy.",
            "Full-match accuracy requires exhaustive labels across direction and camera changes.",
        ],
    }
    if args.assess_target:
        try:
            measured_duration_s = video_duration_s(args.source_video)
        except (OSError, subprocess.CalledProcessError, ValueError) as exc:
            parser.error(f"Cannot measure source-video duration: {exc}")
        measured_sha256 = sha(args.source_video)
        result["measured_source_video_sha256"] = measured_sha256
        result["measured_source_video_duration_s"] = measured_duration_s
        result["acceptance_gate_sha256"] = sha(ROOT / "prototype/event_acceptance.py")
        result["target_assessment"] = assess_recording(
            pred, ref, measured_source_sha256=measured_sha256,
            measured_source_duration_s=measured_duration_s)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps(score, indent=2))


if __name__ == "__main__":
    main()
