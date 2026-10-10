"""Export postscore shared-prefix episodes without changing frozen event counts."""

import argparse
from collections import Counter
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cache_contract import file_sha256  # noqa: E402
from partial_episode_union import build_partial_episode_union  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("handoff", "prefix", "motion", "output"):
        parser.add_argument(f"--{key}", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists")
    handoff, prefix, motion = (
        json.loads(getattr(args, key).read_text()) for key in ("handoff", "prefix", "motion")
    )
    if (
        prefix["motion_sha256"] != file_sha256(args.motion)
        or handoff["input_sha256"]["motion"] != file_sha256(args.motion)
        or prefix["screen_sha256"] != handoff["input_sha256"]["screen"]
        or prefix["source_id"] != handoff["source_id"]
    ):
        parser.error("Evidence artifacts do not share motion, screen and source")
    grouped = build_partial_episode_union(handoff, prefix, motion)
    counts = Counter(row["frozen_event_status"] for row in grouped["candidate_rows"])
    if dict(counts) != handoff["event_status_counts"]:
        raise ValueError("Candidate status ledger differs from frozen handoff")
    result = {
        "status": "postscore_partial_episode_union_not_independent_event_validation",
        "source_id": handoff["source_id"],
        "source_sha256": handoff["source_sha256"],
        "handoff_sha256": file_sha256(args.handoff),
        "prefix_sha256": file_sha256(args.prefix),
        "motion_sha256": file_sha256(args.motion),
        "model_code_sha256": file_sha256(ROOT / "prototype/partial_episode_union.py"),
        "runner_sha256": file_sha256(Path(__file__)),
        "frozen_candidate_count": len(grouped["candidate_rows"]),
        "frozen_event_status_counts": dict(counts),
        "partial_episode_count": len(grouped["episodes"]),
        "partial_episode_candidate_count": sum(
            len(row["candidate_ids"]) for row in grouped["episodes"]
        ),
        **grouped,
        "limitations": [
            "Designed after inspecting an exposed Latvia abstention; not an untouched transfer result.",
            "The overlapping passage is grouped by time, colour and view, not independently verified physical identity.",
            "No partial episode is a complete trajectory, settled board, measured release time or simulation-ready throw.",
            "Frozen screen decisions and all original candidate records remain unchanged.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(
        result["frozen_event_status_counts"],
        result["partial_episode_count"],
        [row["candidate_ids"] for row in result["episodes"]],
    )


if __name__ == "__main__":
    main()
