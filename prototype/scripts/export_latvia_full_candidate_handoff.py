"""Export a lineage-checked ordered Latvia candidate and partial-state handoff."""

from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from full_match_candidate_handoff import build_full_match_candidate_handoff

BASE = ROOT / "validation/throw-event-benchmark/layout-router/full-2024-coverage/latvia24-full-v1"
INPUTS = {
    "timeline": BASE / "timeline.json",
    "raw": BASE / "run-02/events.json",
    "right_variant": BASE / "right-entry-variant-235-225.json",
    "fusion": BASE / "right-entry-camera-aware-fusion.json",
    "partial": BASE / "right-entry-partial-cap-sequence-alignment-gated.json",
    "activity": BASE / "source-activity-coverage-overlay.json",
    "reviews": BASE / "source-pixel-review-ledger.json",
}
OUTPUT = BASE / "full-match-candidate-partial-state-handoff.json"


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    if OUTPUT.exists():
        raise SystemExit("Full candidate handoff already exists")
    inputs = {name: json.loads(path.read_text()) for name, path in INPUTS.items()}
    hashes = {name: digest(path) for name, path in INPUTS.items()}
    if (
        inputs["activity"]["timeline_sha256"] != hashes["timeline"]
        or inputs["fusion"]["left_sha256"] != hashes["timeline"]
        or inputs["fusion"]["right_sha256"] != hashes["right_variant"]
        or inputs["fusion"]["coverage_sha256"] != hashes["activity"]
        or inputs["partial"]["fusion_sha256"] != hashes["fusion"]
    ):
        raise ValueError("Input artifact lineage differs")
    reviewed_manifests = {}
    for name, source in inputs["reviews"]["review_sources"].items():
        manifest_path = BASE / source["manifest"]
        if digest(manifest_path) != source["manifest_sha256"]:
            raise ValueError("Source review manifest differs")
        manifest = json.loads(manifest_path.read_text())
        if manifest["source_sha256"] != inputs["timeline"]["source_sha256"]:
            raise ValueError("Source review video differs")
        if not any(
            (BASE / source["sheet"]).name == sheet.get("path")
            and digest(BASE / source["sheet"]) == sheet["sha256"]
            for sheet in manifest["sheets"]
        ):
            raise ValueError("Source review sheet differs")
        reviewed_manifests[name] = manifest
    for review in inputs["reviews"]["reviews"]:
        source = inputs["reviews"]["review_sources"][review["review_source"]]
        raw_id = review["candidate_id"].split("-")[-1]
        if not any(
            sheet.get("path") == (BASE / source["sheet"]).name and raw_id in sheet["candidate_ids"]
            for sheet in reviewed_manifests[review["review_source"]]["sheets"]
        ):
            raise ValueError("Reviewed candidate is absent from its source sheet")
    result = build_full_match_candidate_handoff(
        inputs["timeline"],
        inputs["raw"],
        inputs["right_variant"],
        inputs["fusion"],
        inputs["partial"],
        inputs["activity"],
        inputs["reviews"],
    )
    result["status"] = "full_match_candidate_and_partial_state_not_throw_truth"
    result["provenance"] = {
        "input_sha256": hashes,
        "model_code_sha256": digest(ROOT / "prototype/full_match_candidate_handoff.py"),
        "runner_sha256": digest(Path(__file__)),
    }
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps(
            {
                "candidate_count": result["candidate_count"],
                "kinds": result["candidate_counts_by_kind"],
                "possible_event_proposal_count": result["possible_event_proposal_count"],
            }
        )
    )


if __name__ == "__main__":
    main()
