"""Add isolated large-cap candidates to primary learned-box episodes."""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cache_contract import file_sha256


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--primary-raw", type=Path, required=True)
    parser.add_argument("--primary-screen", type=Path, required=True)
    parser.add_argument("--cap-screen", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists; preserve the earlier fusion")
    raw = json.loads(args.primary_raw.read_text())
    primary = json.loads(args.primary_screen.read_text())
    cap = json.loads(args.cap_screen.read_text())
    if any(
        item["source_sha256"] != raw["source_sha256"]
        or item["source_interval_s"] != raw["source_interval_s"]
        for item in (primary, cap)
    ) or primary["input_sha256"] != file_sha256(args.primary_raw):
        parser.error("Input source or primary raw/screen mismatch")
    selected = [
        dict(item, evidence_channel="public_box_model")
        for item in primary["corroborated_candidates"]
    ]
    supplemental = []
    withheld = []
    for item in cap["corroborated_candidates"]:
        nearest = min(
            (
                abs(item["crossing_time_s"] - other["crossing_time_s"])
                for other in selected
                if other["gap_id"] == item["gap_id"]
            ),
            default=float("inf"),
        )
        qualified = dict(item, id="cap:" + item["id"], evidence_channel="large_cap_fallback")
        if nearest <= 20:
            withheld.append(
                {
                    "id": qualified["id"],
                    "nearest_primary_s": round(nearest, 3),
                    "reason": "primary_event_within_20s",
                }
            )
        else:
            supplemental.append(qualified)
    result = {
        "status": "development_fused_gap_motion_candidates",
        "source_id": raw["source_id"],
        "source_sha256": raw["source_sha256"],
        "source_interval_s": raw["source_interval_s"],
        "input_sha256": file_sha256(args.primary_raw),
        "primary_screen_sha256": file_sha256(args.primary_screen),
        "cap_screen_sha256": file_sha256(args.cap_screen),
        "runner_sha256": file_sha256(__file__),
        "corroborated_candidates": selected + supplemental,
        "withheld_supplements": withheld,
        "limitations": [
            "Twenty-second episode separation was selected on exposed China 300–600 s footage.",
            "A supplementary cap track is not a confirmed delivered-stone event.",
            "Colour and identity may be wrong even when timing matches a coarse window.",
        ],
    }
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(
        json.dumps(
            {
                "primary": len(selected),
                "supplemented": len(supplemental),
                "withheld_supplements": len(withheld),
            }
        )
    )


if __name__ == "__main__":
    main()
