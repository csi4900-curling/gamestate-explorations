"""Export alternative full-match event observations without forced resolution."""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cache_contract import file_sha256  # noqa: E402
from multiscale_event_handoff import build_multiscale_handoff  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", required=True, type=Path)
    parser.add_argument("--augmented", required=True, type=Path)
    parser.add_argument("--augmented-visual-evidence", type=Path)
    parser.add_argument("--augmented-counter-screen", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Handoff artifact already exists")
    baseline = json.loads(args.baseline.read_text())
    augmented = json.loads(args.augmented.read_text())
    for field in ("source_sha256", "source_interval_s"):
        if baseline[field] != augmented[field]:
            parser.error(f"Ledger {field} mismatch")
    reserved = json.loads((ROOT / "validation/unseen-end/reservation.json").read_text())
    if baseline["source_sha256"] == reserved["source_sha256"]:
        parser.error("Reserved source cannot be used for development handoff")
    evidence = (
        json.loads(args.augmented_visual_evidence.read_text())
        if args.augmented_visual_evidence
        else None
    )
    if evidence is not None and (
        evidence["source_sha256"] != augmented["source_sha256"]
        or evidence["ledger_sha256"] != file_sha256(args.augmented)
    ):
        parser.error("Augmented visual evidence source or ledger mismatch")
    counter_screen = (
        json.loads(args.augmented_counter_screen.read_text())
        if args.augmented_counter_screen
        else None
    )
    if counter_screen is not None and (
        counter_screen["source_sha256"] != augmented["source_sha256"]
        or counter_screen["ledger_sha256"] != file_sha256(args.augmented)
    ):
        parser.error("Augmented counter screen source or ledger mismatch")
    result = build_multiscale_handoff(
        baseline["events"],
        augmented["events"],
        evidence["rows"] if evidence is not None else None,
        counter_screen["rows"] if counter_screen is not None else None,
    )
    result.update(
        {
            "status": "development_multiscale_event_hypotheses_not_verified_game_state",
            "source_sha256": baseline["source_sha256"],
            "source_interval_s": baseline["source_interval_s"],
            "baseline_sha256": file_sha256(args.baseline),
            "augmented_sha256": file_sha256(args.augmented),
            "augmented_visual_evidence_sha256": (
                file_sha256(args.augmented_visual_evidence)
                if args.augmented_visual_evidence
                else None
            ),
            "augmented_counter_screen_sha256": (
                file_sha256(args.augmented_counter_screen)
                if args.augmented_counter_screen
                else None
            ),
            "handoff_code_sha256": file_sha256(ROOT / "prototype/multiscale_event_handoff.py"),
            "runner_sha256": file_sha256(__file__),
        }
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(
        {
            "counter_hypotheses": result["counter_hypothesis_count"],
            "unmerged_visual_proposals": result["unmerged_visual_proposal_count"],
        }
    )


if __name__ == "__main__":
    main()
