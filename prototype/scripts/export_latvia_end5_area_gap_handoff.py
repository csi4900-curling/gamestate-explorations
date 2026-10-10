"""Export Latvia full-match review ledger with the omitted A367 right path."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from prototype.end5_area_gap_enrichment import attach_end5_area_gap_candidate  # noqa: E402


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("ledger", "audit", "right-scan", "output"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists; preserve previous handoff")
    ledger = json.loads(args.ledger.read_text())
    audit = json.loads(args.audit.read_text())
    scan = json.loads(args.right_scan.read_text())
    source_sheet = args.audit.parent / audit["source_sheet"]
    if (audit["previous_ledger_sha256"] != digest(args.ledger) or
            audit["right_area_scan_sha256"] != digest(args.right_scan) or
            audit["source_sheet_sha256"] != digest(source_sheet) or
            audit["runner_sha256"] != digest(
                ROOT / "prototype/scripts/audit_latvia_end5_area_gap.py")):
        raise ValueError("A367 audit lineage differs")
    output = attach_end5_area_gap_candidate(ledger, audit, scan)
    output["provenance"]["end5_area_gap_enrichment"] = {
        "previous_ledger_sha256": digest(args.ledger),
        "source_audit_sha256": digest(args.audit),
        "right_area_scan_sha256": digest(args.right_scan),
        "source_sheet_sha256": digest(source_sheet),
        "enrichment_code_sha256": digest(ROOT / "prototype/end5_area_gap_enrichment.py"),
        "runner_sha256": digest(Path(__file__)),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, allow_nan=False) + "\n")
    print(json.dumps({
        "candidate_count": output["candidate_count"],
        "review_proposal_count": output["development_possible_event_review_count"],
        "new_candidate_id": "right_area:R01:A367",
        "physical_throw_count_verified": output["physical_throw_count_verified"],
    }))


if __name__ == "__main__":
    main()
