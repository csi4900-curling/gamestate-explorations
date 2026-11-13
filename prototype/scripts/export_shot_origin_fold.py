"""Export one source-scoped fold from a preserved cross-match shot probe."""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cache_contract import file_sha256


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--folds", type=Path, required=True)
    parser.add_argument("--heldout", required=True)
    parser.add_argument("--review", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists; preserve first exported fold")
    cv = json.loads(args.folds.read_text())
    manifest = json.loads((args.review / "manifest.json").read_text())
    fold = next((row for row in cv["folds"] if row["heldout"] == args.heldout), None)
    if fold is None or len(fold["rows"]) != len(manifest["shots"]):
        parser.error("Fold does not match shot review")
    if [row["shot_id"] for row in fold["rows"]] != [row["id"] for row in manifest["shots"]]:
        parser.error("Fold shot order does not match review")
    result = {
        "status": "development_exported_cross_match_shot_origin_fold",
        "source_id": manifest["source_id"],
        "source_sha256": manifest["source_sha256"],
        "source_interval_s": manifest["source_interval_s"],
        "folds_sha256": file_sha256(args.folds),
        "review_sha256": file_sha256(args.review / "manifest.json"),
        "runner_sha256": file_sha256(__file__),
        "model_sha256": fold["model_sha256"],
        "rows": fold["rows"],
    }
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"shots": len(result["rows"]), "heldout": args.heldout}))


if __name__ == "__main__":
    main()
