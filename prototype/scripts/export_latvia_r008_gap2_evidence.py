"""Export Latvia full-match handoff with R008 stone-pixel association evidence."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from prototype.r008_gap2_evidence_enrichment import attach_r008_gap2_evidence  # noqa: E402


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("ledger", "audit", "video", "one-gap-scan", "area-gap2-scan",
                 "global-gap2-scan", "source-review", "output"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists; preserve previous handoff")
    ledger = json.loads(args.ledger.read_text())
    audit = json.loads(args.audit.read_text())
    inputs = audit["input_sha256"]
    source_sheet = args.source_review.parent / "sheet-01.jpg"
    if (inputs["previous_ledger"] != digest(args.ledger) or
            inputs["one_second_gap_area_scan"] != digest(args.one_gap_scan) or
            inputs["local_area_gap2_scan"] != digest(args.area_gap2_scan) or
            inputs["local_global_gap2_scan"] != digest(args.global_gap2_scan) or
            inputs["archived_source_review"] != digest(args.source_review) or
            inputs["archived_source_sheet"] != digest(source_sheet) or
            audit["source_video_sha256"] != digest(args.video) or
            audit["runner_sha256"] != digest(
                ROOT / "prototype/scripts/audit_latvia_r008_gap2_recovery.py")):
        raise ValueError("R008 audit lineage differs")
    output = attach_r008_gap2_evidence(ledger, audit)
    output["provenance"]["r008_gap2_evidence_enrichment"] = {
        "previous_ledger_sha256": digest(args.ledger),
        "audit_sha256": digest(args.audit),
        "source_video_sha256": digest(args.video),
        "enrichment_code_sha256": digest(
            ROOT / "prototype/r008_gap2_evidence_enrichment.py"),
        "runner_sha256": digest(Path(__file__)),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, allow_nan=False) + "\n")
    print(json.dumps({
        "candidate_count": output["candidate_count"],
        "review_proposal_count": output["development_possible_event_review_count"],
        "r008_source_pixel_class": next(row["source_pixel_review"][
            "source_pixel_class"] for row in output["ordered_candidates"] if
            row["candidate_id"] == "right:R008"),
        "physical_throw_count_verified": output["physical_throw_count_verified"],
    }))


if __name__ == "__main__":
    main()
