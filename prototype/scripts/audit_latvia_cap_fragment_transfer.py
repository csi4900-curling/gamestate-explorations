"""Check frozen Latvia continuation frames for Czech fragment-merge geometry."""

from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cap_fragment_merge import merge_cap_fragments

BASE = ROOT / "validation/throw-event-benchmark/canada-latvia-2024"
VIDEO = BASE / "source-1080p-1650-2760.mp4"
BASELINE = BASE / "board-blind-cap-continuation-transfer-development.json"
OUT = BASE / "cap-fragment-merge-recorded-step-transfer-development.json"


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def main():
    if OUT.exists():
        raise ValueError("Latvia fragment-transfer output already exists")
    baseline = json.loads(BASELINE.read_text())
    if (
        digest(VIDEO) != baseline["source_video_sha256"]
        or baseline["selector_code_sha256"] != digest(ROOT / "prototype/causal_cap_continuation.py")
        or baseline["component_code_sha256"] != digest(ROOT / "prototype/local_colour_cap_probe.py")
    ):
        raise ValueError("Frozen Latvia source or code differs")
    rows = []
    for candidate in baseline["rows"]:
        steps = []
        for step in candidate["steps"]:
            merged = merge_cap_fragments(step["components"])
            pairs = [
                item["merged_source_component_indices"]
                for item in merged
                if len(item["merged_source_component_indices"]) > 1
            ]
            steps.append(
                {
                    "source_time_s": step["source_time_s"],
                    "original_component_count": len(step["components"]),
                    "fragment_merge_source_index_pairs": pairs,
                    "baseline_decision_status": step["decision"]["status"],
                }
            )
        rows.append(
            {
                "candidate_id": candidate["candidate_id"],
                "eligibility_reason": candidate["eligibility_reason"],
                "recorded_step_count": len(steps),
                "fragment_merge_count": sum(
                    len(step["fragment_merge_source_index_pairs"]) for step in steps
                ),
                "baseline_abstention_reason": candidate["abstention_reason"],
                "steps": steps,
            }
        )
    total = sum(row["fragment_merge_count"] for row in rows)
    OUT.write_text(
        json.dumps(
            {
                "status": "recorded_step_fragment_geometry_transfer_not_new_source_replay",
                "source_video_sha256": baseline["source_video_sha256"],
                "input_sha256": {"frozen_latvia_continuation": digest(BASELINE)},
                "code_sha256": {
                    "runner": digest(Path(__file__)),
                    "fragment_merge": digest(ROOT / "prototype/cap_fragment_merge.py"),
                },
                "candidate_count": len(rows),
                "recorded_step_count": sum(row["recorded_step_count"] for row in rows),
                "fragment_merge_count": total,
                "rows": rows,
                "limitations": [
                    "This checks only component sets already decoded by the frozen Latvia continuation; no new source frames are sampled.",
                    "With no fragment merges on recorded steps, the merge cannot change a deterministic selector before its existing abstention in these cases.",
                    "The recording was exposed in development, and source paths and board observations are not independently verified physical identities.",
                ],
            },
            indent=2,
        )
        + "\n"
    )
    print(
        json.dumps(
            {
                "candidates": len(rows),
                "recorded_steps": sum(row["recorded_step_count"] for row in rows),
                "fragment_merges": total,
            }
        )
    )


if __name__ == "__main__":
    main()
