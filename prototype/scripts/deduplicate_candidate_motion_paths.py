"""Deduplicate candidate passages sharing the same timed provisional path."""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cache_contract import file_sha256  # noqa: E402
from motion_path_dedup import deduplicate_motion_paths  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidates", type=Path, required=True)
    parser.add_argument("--motion", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Deduplication artifact already exists")
    candidates = json.loads(args.candidates.read_text())
    motion = json.loads(args.motion.read_text())
    joined = deduplicate_motion_paths(candidates["events"], motion["rows"])
    selected = {
        r["candidate_id"]
        for r in motion["rows"]
        if r["selection"]["status"] == "provisional_unique_far_entry_motion_path"
    }
    retained = selected & set(joined["retained_candidate_ids"])
    result = {
        "status": "postscore_development_shared_motion_dedup_not_event_validation",
        "source_id": candidates["source_id"],
        "source_sha256": candidates["source_sha256"],
        "source_interval_s": candidates["source_interval_s"],
        "candidates_sha256": file_sha256(args.candidates),
        "motion_sha256": file_sha256(args.motion),
        "dedup_code_sha256": file_sha256(ROOT / "prototype/motion_path_dedup.py"),
        "runner_sha256": file_sha256(__file__),
        **joined,
        "events": [event for event in candidates["events"] if event["id"] in retained],
        "limitations": [
            "Timed path overlap suggests duplicate passage proposals, not independently verified physical identity.",
            "This rule was created after seeing Estonia S23/S24 and is postscore in-sample development.",
            "Accepted paths may contain explicitly unobserved intervals and borrowed camera transforms.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print("pairs", joined["pairs"], "accepted", len(result["events"]))


if __name__ == "__main__":
    main()
