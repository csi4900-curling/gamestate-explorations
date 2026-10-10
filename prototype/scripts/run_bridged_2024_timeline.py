"""Run unchanged 2024 event stages over a postscore bridged preflight."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "prototype"))
from throw_timeline import assemble_timeline
from prototype.scripts.run_throw_pipeline import run_adapter


def digest(path):
    h = sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", required=True, type=Path)
    parser.add_argument("--preflight", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    preflight = json.loads(args.preflight.read_text())
    if preflight.get("bridge_code_sha256") != digest(ROOT / "prototype/layout_gap_bridge.py"):
        parser.error("Bridged preflight uses different bridge code")
    if digest(args.video) != preflight["source_sha256"]:
        parser.error("Source differs from bridged preflight")
    reservation = json.loads((ROOT / "validation/unseen-end/reservation.json").read_text())
    if preflight["source_sha256"] == reservation["source_sha256"]:
        parser.error("Reserved source cannot be used for development")
    if args.output_dir.exists() and not args.resume:
        parser.error("Output exists; use --resume to verify and continue")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    completed = []
    index = 0
    for run in preflight["runs"]:
        if run["layout"] == "unknown":
            continue
        if run["layout"] != "split_2024":
            parser.error("This runner accepts only 2024 split runs")
        index += 1
        start, end = run["interval_s"]
        artifact, result = run_adapter(
            args.video, preflight["source_id"], preflight["source_sha256"],
            "split_2024", start, end, args.output_dir / f"run-{index:02}",
            resume=args.resume, preflight_path=args.preflight)
        completed.append((run, result, artifact.relative_to(args.output_dir)))
    timeline = assemble_timeline(preflight, completed)
    timeline.update({
        "status": "postscore_bridged_partial_candidate_timeline_not_event_validation",
        "bridged_preflight_artifact_sha256": digest(args.preflight),
        "runner_sha256": digest(Path(__file__)),
        "limitations": timeline["limitations"] + [
            "Bridged Scotland footage was selected after seeing the original routing failure.",
            "No complete-match physical throw reference or precision/recall follows from this pass.",
        ],
    })
    output = args.output_dir / "timeline.json"
    value = json.dumps(timeline, indent=2) + "\n"
    if output.exists() and output.read_text() != value:
        raise ValueError("Existing timeline differs from verified adapter stages")
    if not output.exists():
        output.write_text(value)
    print(json.dumps({"observed": timeline["observed_event_count"],
                      "coverage_gaps": timeline["coverage_gaps_s"]}))


if __name__ == "__main__":
    main()
