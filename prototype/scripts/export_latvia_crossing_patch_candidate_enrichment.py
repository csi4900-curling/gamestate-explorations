"""Enrich the Latvia full-match candidate ledger with frozen patch scores."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from crossing_patch_candidate_enrichment import enrich_full_match_candidates  # noqa: E402


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("union", "score", "packet", "model", "output"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    parser.add_argument("--score-runner", type=Path, default=ROOT /
                        "prototype/scripts/score_latvia_italy_frozen_crossing_patches.py")
    parser.add_argument("--selection", type=Path, default=ROOT /
                        "validation/official-shot-sequence/latvia-italy-crossing-patch-source-class-selection.json")
    parser.add_argument("--postscore-audit", type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists; preserve the previous handoff")
    union = json.loads(args.union.read_text())
    score = json.loads(args.score.read_text())
    manifest_path = args.packet / "manifest.json"
    packet = json.loads(manifest_path.read_text())
    if (score["packet_manifest_sha256"] != digest(manifest_path) or
            score["model_sha256"] != digest(args.model) or
            score["feature_code_sha256"] != digest(
                ROOT / "prototype/stone_patch_detector.py") or
            score["runner_sha256"] != digest(args.score_runner) or
            packet["selection_sha256"] != digest(args.selection)):
        raise ValueError("Crossing patch evidence lineage differs")
    postscore = json.loads(args.postscore_audit.read_text()) if args.postscore_audit else None
    if postscore:
        images = (postscore["pages"] if "pages" in postscore else
                  [{"image": postscore["image"], "sha256": postscore[
                      "image_sha256"]}])
        audit_runner = (ROOT / "prototype/scripts/audit_latvia_all_negative_patches.py"
                        if "pages" in postscore else
                        ROOT / "prototype/scripts/audit_latvia_low_patch_source.py")
        if (postscore["score_sha256"] != digest(args.score) or
                postscore["packet_manifest_sha256"] != digest(manifest_path) or
                postscore["runner_sha256"] != digest(audit_runner) or
                any(image["sha256"] != digest(args.postscore_audit.parent /
                    image["image"]) for image in images)):
            raise ValueError("Postscore source review lineage differs")
    output = enrich_full_match_candidates(union, score, packet, postscore)
    output["provenance"]["crossing_patch_enrichment"] = {
        "union_sha256": digest(args.union),
        "score_sha256": digest(args.score),
        "packet_manifest_sha256": digest(manifest_path),
        "selection_sha256": digest(args.selection),
        "model_sha256": digest(args.model),
        "score_runner_sha256": digest(args.score_runner),
        "postscore_audit_sha256": digest(args.postscore_audit)
            if args.postscore_audit else None,
        "model_code_sha256": digest(
            ROOT / "prototype/crossing_patch_candidate_enrichment.py"),
        "runner_sha256": digest(Path(__file__)),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"candidates": output["candidate_count"],
                      "graded_patch_scores": output["crossing_patch_scored_left_count"],
                      "possible_event_reviews": output[
                          "development_possible_event_review_count"],
                      "physical_throw_count_verified": output[
                          "physical_throw_count_verified"]}))


if __name__ == "__main__":
    main()
