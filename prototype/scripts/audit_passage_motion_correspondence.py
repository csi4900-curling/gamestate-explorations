"""Diagnose candidate passages against window-conditioned receiving motion."""

import argparse
from collections import Counter
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cache_contract import file_sha256  # noqa: E402
from motion_correspondence import join_passages_to_motion  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidates", type=Path, required=True)
    parser.add_argument("--motion", type=Path, required=True)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--max-delay-s", type=float, default=6.0)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Correspondence artifact already exists")
    candidates = json.loads(args.candidates.read_text())
    motion = json.loads(args.motion.read_text())
    reference = json.loads(args.reference.read_text())
    if candidates["source_id"] != reference["source_id"] or (
        candidates["source_sha256"] != reference["source_sha256"]
    ):
        parser.error("Candidate source differs from reference source")
    if file_sha256(args.reference) != motion["reference_sha256"]:
        parser.error("Motion audit reference differs")
    joined = join_passages_to_motion(
        candidates["events"], motion["rows"], max_delay_s=args.max_delay_s
    )
    result = {
        "status": "development_window_conditioned_passage_motion_diagnostic_not_detector_score",
        "source_id": candidates["source_id"],
        "candidate_source_sha256": candidates["source_sha256"],
        "motion_source_sha256": motion["source_video_sha256"],
        "candidates_sha256": file_sha256(args.candidates),
        "motion_sha256": file_sha256(args.motion),
        "reference_sha256": file_sha256(args.reference),
        "joiner_sha256": file_sha256(ROOT / "prototype/motion_correspondence.py"),
        "runner_sha256": file_sha256(__file__),
        "max_delay_s": args.max_delay_s,
        "passage_status_counts": dict(Counter(r["status"] for r in joined["passages"])),
        "path_status_counts": dict(Counter(r["status"] for r in joined["paths"])),
        **joined,
        "limitations": [
            "Receiving paths were selected inside agent-authored coarse reference windows, so their absence elsewhere cannot reject a full-video candidate.",
            "The same developer inspected candidate disagreements and selected motion rules; this is in-sample correspondence, not an independent filter benchmark.",
            "The candidate source is the full-match 360p copy; motion comes from a separately aligned 1080p interval copy of the same broadcast.",
            "Temporal, colour, and view agreement do not independently prove a persistent physical stone identity.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(result["passage_status_counts"], result["path_status_counts"])


if __name__ == "__main__":
    main()
