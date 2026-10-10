"""Export local origin-model effects of isolated possible camera edits."""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cache_contract import file_sha256  # noqa: E402
from cut_effect_audit import audit_cut_effects  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--edit-audit", type=Path, required=True)
    parser.add_argument("--baseline-origins", type=Path, required=True)
    parser.add_argument("--augmented-origins", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Cut-effect audit already exists")
    edits = json.loads(args.edit_audit.read_text())
    baseline = json.loads(args.baseline_origins.read_text())
    augmented = json.loads(args.augmented_origins.read_text())
    if len({d["source_sha256"] for d in (edits, baseline, augmented)}) != 1:
        parser.error("Source hash mismatch")
    if baseline["source_interval_s"] != augmented["source_interval_s"]:
        parser.error("Source interval mismatch")
    reserved = json.loads((ROOT / "validation/unseen-end/reservation.json").read_text())
    if baseline["source_sha256"] == reserved["source_sha256"]:
        parser.error("Reserved source cannot be used for development audit")
    result = audit_cut_effects(edits["rows"], baseline["rows"], augmented["rows"])
    result.update({
        "status": "development_source_only_origin_response_not_event_validation",
        "source_sha256": baseline["source_sha256"],
        "source_interval_s": baseline["source_interval_s"],
        "edit_audit_sha256": file_sha256(args.edit_audit),
        "baseline_origins_sha256": file_sha256(args.baseline_origins),
        "augmented_origins_sha256": file_sha256(args.augmented_origins),
        "audit_code_sha256": file_sha256(ROOT / "prototype/cut_effect_audit.py"),
        "runner_sha256": file_sha256(__file__),
    })
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(result["origin_pattern_counts"])


if __name__ == "__main__":
    main()
