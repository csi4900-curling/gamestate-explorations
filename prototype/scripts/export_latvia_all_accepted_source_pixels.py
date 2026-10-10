"""Export full-match handoff with source-pixel review of all accepted left crossings."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from prototype.positive_patch_source_enrichment import attach_positive_source_reviews  # noqa: E402


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("negative-ledger", "positive-audit", "score", "packet", "output"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists; preserve the previous handoff")
    ledger = json.loads(args.negative_ledger.read_text())
    audit = json.loads(args.positive_audit.read_text())
    manifest_path = args.packet / "manifest.json"
    if (audit["score_sha256"] != digest(args.score) or
            audit["packet_manifest_sha256"] != digest(manifest_path) or
            audit["runner_sha256"] != digest(
                ROOT / "prototype/scripts/audit_latvia_all_positive_patches.py") or
            audit["helper_code_sha256"] != digest(
                ROOT / "prototype/scripts/audit_latvia_all_negative_patches.py") or
            any(page["sha256"] != digest(args.positive_audit.parent /
                page["image"]) for page in audit["pages"])):
        raise ValueError("Positive source review lineage differs")
    output = attach_positive_source_reviews(ledger, audit)
    output["provenance"]["positive_patch_source_enrichment"] = {
        "negative_ledger_sha256": digest(args.negative_ledger),
        "positive_audit_sha256": digest(args.positive_audit),
        "score_sha256": digest(args.score),
        "packet_manifest_sha256": digest(manifest_path),
        "model_code_sha256": digest(
            ROOT / "prototype/positive_patch_source_enrichment.py"),
        "runner_sha256": digest(Path(__file__)),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"accepted_left_source_reviewed": output[
        "source_pixel_reviewed_accepted_left_count"],
        "source_class_counts": output["accepted_left_source_pixel_class_counts"],
        "physical_throw_count_verified": output["physical_throw_count_verified"]}))


if __name__ == "__main__":
    main()
