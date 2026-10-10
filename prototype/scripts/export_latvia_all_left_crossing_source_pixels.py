"""Export full-match handoff with accepted and withheld left pixel reviews."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from prototype.withheld_patch_source_enrichment import attach_withheld_source_reviews  # noqa: E402


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("accepted-ledger", "withheld-audit", "score", "packet", "output"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists; preserve the previous handoff")
    ledger = json.loads(args.accepted_ledger.read_text())
    audit = json.loads(args.withheld_audit.read_text())
    manifest_path = args.packet / "manifest.json"
    packet = json.loads(manifest_path.read_text())
    score = json.loads(args.score.read_text())
    if (audit["score_sha256"] != digest(args.score) or
            audit["packet_manifest_sha256"] != digest(manifest_path) or
            packet["source_video_sha256"] != ledger["source_sha256"] or
            score["packet_manifest_sha256"] != digest(manifest_path) or
            audit["runner_sha256"] != digest(
                ROOT / "prototype/scripts/audit_latvia_withheld_crossing_patches.py") or
            any(page["sha256"] != digest(args.withheld_audit.parent / page["image"])
                for page in audit["pages"])):
        raise ValueError("Withheld source review lineage differs")
    score_by_id = {row["event_id"]: row for row in score["rows"]}
    if (len(score_by_id) != 47 or len(packet["rows"]) != 47 or
            {row["event_id"] for row in packet["rows"]} != set(score_by_id) or
            {row["candidate_id"] for row in audit["rows"]} != set(score_by_id) or
            any(abs(row["frozen_patch_mean_score"] - score_by_id[
                row["candidate_id"]]["mean_score"]) > 0.000001 or
                row["frozen_patch_model_positive"] != score_by_id[
                    row["candidate_id"]]["predicted_stone_like"]
                for row in audit["rows"])):
        raise ValueError("Withheld audit rows differ from frozen packet scores")
    output = attach_withheld_source_reviews(ledger, audit)
    output["provenance"]["withheld_patch_source_enrichment"] = {
        "accepted_ledger_sha256": digest(args.accepted_ledger),
        "withheld_audit_sha256": digest(args.withheld_audit),
        "score_sha256": digest(args.score),
        "packet_manifest_sha256": digest(manifest_path),
        "model_code_sha256": digest(
            ROOT / "prototype/withheld_patch_source_enrichment.py"),
        "runner_sha256": digest(Path(__file__)),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, allow_nan=False) + "\n")
    print(json.dumps({
        "accepted_left_source_reviewed": output["source_pixel_reviewed_accepted_left_count"],
        "withheld_left_source_reviewed": output["source_pixel_reviewed_withheld_left_count"],
        "withheld_class_counts": output["withheld_left_source_pixel_class_counts"],
        "physical_throw_count_verified": output["physical_throw_count_verified"],
    }))


if __name__ == "__main__":
    main()
