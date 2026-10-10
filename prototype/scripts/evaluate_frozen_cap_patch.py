"""Score one labelled development match with previously frozen patch weights."""

import argparse
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cache_contract import file_sha256
from scripts.score_cap_patch_transfer import counts, make_features


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review", type=Path, required=True)
    parser.add_argument("--source", required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists; preserve first frozen score")
    manifest = json.loads((args.review / "manifest.json").read_text())
    labels = json.loads((args.review / "labels.json").read_text())
    if args.source not in labels:
        parser.error("No labels for requested source")
    rows = make_features(manifest, {args.source: labels[args.source]})
    features = np.stack([row["feature"] for row in rows])
    with np.load(args.model, allow_pickle=False) as model:
        scores = ((features - model["mean"]) / model["scale"]) @ model["weights"].ravel()
        scores += model["intercept"].item()
        threshold = model["threshold"].item()
    for row, score in zip(rows, scores):
        row["score"] = float(score)
        row["predicted"] = int(score >= threshold)
        del row["feature"]
    result = {
        "status": "development_frozen_cross_match_cap_patch_probe",
        "source_id": args.source,
        "review_manifest_sha256": file_sha256(args.review / "manifest.json"),
        "labels_sha256": file_sha256(args.review / "labels.json"),
        "model_sha256": file_sha256(args.model),
        "runner_sha256": file_sha256(__file__),
        "threshold": threshold, "score": counts(rows), "rows": rows,
        "limitations": [
            "Selected tracks and three frames per track are not an unbiased sample.",
            "Labels are developer-authored visual review, not independent ground truth.",
            "Stone patch identity is not throw identity or event precision/recall.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result["score"], indent=2))


if __name__ == "__main__":
    main()
