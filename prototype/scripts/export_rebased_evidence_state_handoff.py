"""Export rebased video events and partial boards with end-score constraints."""

import argparse
from collections import Counter
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cache_contract import file_sha256  # noqa: E402
from evidence_game_state_handoff import build_evidence_handoff  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("candidates", "screen", "motion", "hold", "source-motion",
                "boards", "comparisons", "official-end-scores", "output"):
        parser.add_argument(f"--{key}", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Evidence handoff already exists")
    inputs = {key: json.loads(getattr(args, key.replace('-', '_')).read_text())
              for key in ("candidates", "screen", "motion", "hold",
                          "source-motion", "boards", "comparisons",
                          "official-end-scores")}
    digests = {key: file_sha256(getattr(args, key.replace('-', '_')))
               for key in inputs}
    candidates, screen, motion, boards, comparisons = (
        inputs[key] for key in ("candidates", "screen", "motion", "boards",
                               "comparisons"))
    if (screen["candidates_sha256"] != digests["candidates"] or
            screen["motion_sha256"] != digests["motion"] or
            motion["hold_sha256"] != digests["hold"] or
            inputs["hold"]["motion_sha256"] != digests["source-motion"] or
            inputs["source-motion"]["candidates_sha256"] != digests["candidates"] or
            boards["candidates_sha256"] != digests["candidates"] or
            boards["screen_sha256"] != digests["screen"] or
            boards["motion_sha256"] != digests["motion"] or
            boards["hold_sha256"] != digests["hold"] or
            boards["source_motion_sha256"] != digests["source-motion"] or
            comparisons["boards_sha256"] != digests["boards"] or
            comparisons["candidates_sha256"] != digests["candidates"] or
            comparisons["screen_sha256"] != digests["screen"]):
        parser.error("Evidence input provenance chain differs")
    official = inputs["official-end-scores"]
    if official["video_source_id"] != candidates["source_id"]:
        parser.error("Official score context names a different video source")
    timeline = build_evidence_handoff(candidates, screen, motion, boards,
                                      comparisons)
    status_counts = dict(Counter(row["event_status"] for row in timeline))
    output = {
        "status": "provisional_video_evidence_timeline_not_complete_game_state",
        "source_id": candidates["source_id"],
        "source_sha256": candidates["source_sha256"],
        "source_interval_s": candidates["source_interval_s"],
        "input_sha256": digests,
        "model_code_sha256": file_sha256(ROOT / "prototype" /
                                         "evidence_game_state_handoff.py"),
        "runner_sha256": file_sha256(Path(__file__)),
        "event_status_counts": status_counts,
        "timeline": timeline,
        "independent_end_score_context": {
            "status": official["status"],
            "teams": official["teams"],
            "completed_ends": official["completed_ends"],
            "event_to_end_alignment_verified": False,
            "event_to_score_change_alignment_verified": False,
        },
        "limitations": [
            "Provisional event support is not independent precision or recall validation.",
            "Passage timestamps are observed video cues, not release timestamps.",
            "Receiving paths and boards use unvalidated camera-local projection.",
            "Partial boards do not identify physical stones or prove complete end states.",
            "Official end scores are independent context but are not aligned to these video events.",
            "No timeline item is ready for physical simulation or coaching claims.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps(status_counts, indent=2))


if __name__ == "__main__":
    main()
