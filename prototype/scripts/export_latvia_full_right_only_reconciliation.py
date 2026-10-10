"""Export the full-match ledger accounting for all frozen area right-only paths."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from prototype.full_right_only_reconciliation import reconcile_full_right_only  # noqa: E402


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("ledger", "audit", "right-scan", "episodes", "video", "output"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists; preserve previous handoff")
    ledger = json.loads(args.ledger.read_text())
    audit = json.loads(args.audit.read_text())
    scan = json.loads(args.right_scan.read_text())
    episodes = json.loads(args.episodes.read_text())
    if (audit["previous_ledger_sha256"] != digest(args.ledger) or
            audit["right_area_scan_sha256"] != digest(args.right_scan) or
            audit["episode_inventory_sha256"] != digest(args.episodes) or
            audit["source_video_sha256"] != digest(args.video) or
            audit["runner_sha256"] != digest(
                ROOT / "prototype/scripts/audit_latvia_remaining_right_only.py") or
            any(row["source_sheet_sha256"] != digest(
                args.audit.parent / row["source_sheet"])
                for row in audit["rows"])):
        raise ValueError("Remaining right-only source review lineage differs")
    output = reconcile_full_right_only(ledger, episodes, scan, audit)
    output["provenance"]["full_right_only_reconciliation"] = {
        "previous_ledger_sha256": digest(args.ledger),
        "source_audit_sha256": digest(args.audit),
        "right_area_scan_sha256": digest(args.right_scan),
        "episodes_sha256": digest(args.episodes),
        "source_video_sha256": digest(args.video),
        "reconciliation_code_sha256": digest(
            ROOT / "prototype/full_right_only_reconciliation.py"),
        "runner_sha256": digest(Path(__file__)),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, allow_nan=False) + "\n")
    print(json.dumps({
        "candidate_count": output["candidate_count"],
        "possible_event_review_count": output["development_possible_event_review_count"],
        "right_only_accounting": output["right_area_right_only_accounting_counts"],
        "physical_throw_count_verified": output["physical_throw_count_verified"],
    }))


if __name__ == "__main__":
    main()
