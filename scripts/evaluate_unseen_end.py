"""Seal independently reviewed labels or score explicit model outputs; never label for the reviewer."""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "prototype"))
from cache_contract import file_sha256
from end_evaluation import evaluate_end, validate_reference


def write_new(path, value):
    path = Path(path)
    with path.open("x") as f:
        f.write(json.dumps(value, indent=2, allow_nan=False) + "\n")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    seal = sub.add_parser("seal")
    seal.add_argument("--reference", type=Path, required=True)
    seal.add_argument("--video", type=Path, required=True)
    seal.add_argument("--output", type=Path, required=True)
    score = sub.add_parser("score")
    score.add_argument("--seal", type=Path, required=True)
    score.add_argument("--predictions", type=Path, required=True)
    score.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    if args.output.exists():
        p.error("Output exists; use a new versioned path")
    if args.command == "seal":
        ref = json.loads(args.reference.read_text())
        validate_reference(ref)
        digest = file_sha256(args.video)
        if ref.get("source_sha256") not in (None, digest):
            p.error("Reference source hash differs from video")
        if ref.get("source_file") != args.video.name:
            p.error("Reference filename differs from video")
        if ref.get("source_size_bytes") != args.video.stat().st_size:
            p.error("Reference file size differs from video")
        ref["source_sha256"] = digest
        write_new(
            args.output,
            {
                "schema": 1,
                "reference_input_sha256": file_sha256(args.reference),
                "reference": ref,
                "note": "Reviewer declaration; integrity seal does not independently verify honesty or label accuracy.",
            },
        )
        digest_path = args.output.with_suffix(args.output.suffix + ".sha256")
        write_new(digest_path, {"sha256": file_sha256(args.output)})
        print(f"Sealed reference: {args.output}; preserve {digest_path}")
    else:
        expected = json.loads(args.seal.with_suffix(args.seal.suffix + ".sha256").read_text())[
            "sha256"
        ]
        if file_sha256(args.seal) != expected:
            p.error("Sealed reference changed")
        ref = json.loads(args.seal.read_text())["reference"]
        pred = json.loads(args.predictions.read_text())
        result = evaluate_end(ref, pred)
        result["reference_seal_sha256"] = expected
        result["predictions_sha256"] = file_sha256(args.predictions)
        result["evaluator_sha256"] = file_sha256(ROOT / "prototype/end_evaluation.py")
        result["model_freeze"] = pred.get("model_freeze")
        result["protocol_compliance"] = (
            "Requires review of pre-inference model/config freeze and reviewer independence; scoring alone does not certify compliance."
        )
        write_new(args.output, result)
        print(
            json.dumps(
                {k: v for k, v in result.items() if k in ("events", "cross_view_identity")},
                indent=2,
            )
        )


if __name__ == "__main__":
    main()
