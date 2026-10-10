"""Export appearance/release evidence patterns for all visual-only candidates."""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cache_contract import file_sha256  # noqa: E402
from visual_only_evidence_join import join_evidence  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--patch-audit", type=Path, required=True)
    parser.add_argument("--release-audit", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Joined evidence artifact already exists")
    patch = json.loads(args.patch_audit.read_text())
    release = json.loads(args.release_audit.read_text())
    for field in ("source_sha256", "source_interval_s", "ledger_sha256"):
        if patch[field] != release[field]:
            parser.error(f"Evidence {field} mismatch")
    reserved = json.loads((ROOT / "validation/unseen-end/reservation.json").read_text())
    if patch["source_sha256"] == reserved["source_sha256"]:
        parser.error("Reserved source cannot be used for development join")
    result = join_evidence(patch["rows"], release["rows"])
    result.update({
        "status": "development_visual_only_evidence_patterns_not_event_filter",
        "source_sha256": patch["source_sha256"],
        "source_interval_s": patch["source_interval_s"],
        "ledger_sha256": patch["ledger_sha256"],
        "patch_audit_sha256": file_sha256(args.patch_audit),
        "release_audit_sha256": file_sha256(args.release_audit),
        "join_code_sha256": file_sha256(ROOT / "prototype/visual_only_evidence_join.py"),
        "runner_sha256": file_sha256(__file__),
    })
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(result["evidence_pattern_counts"])


if __name__ == "__main__":
    main()
