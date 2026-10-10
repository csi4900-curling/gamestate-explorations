"""Apply motion-support colour refinement to primary events in a fused screen."""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cache_contract import file_sha256
from episode_colour_support import refine_episode_colours


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--primary-raw", type=Path, required=True)
    parser.add_argument("--primary-screen", type=Path, required=True)
    parser.add_argument("--fused-screen", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists; preserve the earlier result")
    raw = json.loads(args.primary_raw.read_text())
    primary = json.loads(args.primary_screen.read_text())
    fused = json.loads(args.fused_screen.read_text())
    if (primary["input_sha256"] != file_sha256(args.primary_raw)
            or fused["input_sha256"] != file_sha256(args.primary_raw)):
        parser.error("Primary raw/screen/fusion mismatch")
    if any(row["source_sha256"] != raw["source_sha256"] for row in (primary, fused)):
        parser.error("Source fingerprint mismatch")
    support = refine_episode_colours(raw["motion_candidates"], primary["decisions"])
    support_by_id = {row["id"]: row for row in support}
    confirmed = []
    for item in fused["corroborated_candidates"]:
        updated = dict(item)
        if item["evidence_channel"] == "public_box_model":
            row = support_by_id[item["id"]]
            updated["colour"] = row["colour"]
            updated["colour_support"] = row
        confirmed.append(updated)
    result = dict(fused)
    result.update({
        "status": "development_colour_refined_gap_motion_candidates",
        "input_sha256": file_sha256(args.primary_raw),
        "primary_screen_sha256": file_sha256(args.primary_screen),
        "fused_screen_sha256": file_sha256(args.fused_screen),
        "colour_model_sha256": file_sha256(ROOT / "prototype/episode_colour_support.py"),
        "colour_runner_sha256": file_sha256(__file__),
        "colour_decisions": support,
        "corroborated_candidates": confirmed,
    })
    result["limitations"] = fused["limitations"] + [
        "Colour refinement was fitted to exposed China 600–885 s errors.",
        "It does not validate delivered-stone identity across camera cuts.",
    ]
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"events": len(confirmed), "colour_changes": sum(
        row["colour_changed"] for row in support)}))


if __name__ == "__main__":
    main()
