"""Derive weak delivery windows from a high-visibility counter audit."""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cache_contract import file_sha256


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists; preserve reference selection")
    audit = json.loads(args.audit.read_text())
    if audit["visible_sample_count"] / audit["sample_count"] < 0.9:
        parser.error("Counter readability below 90%; this proxy protocol does not apply")
    if audit["unresolved_counter_changes"]:
        parser.error("Unresolved count changes prevent an exhaustive proxy")
    lo, hi = audit["source_interval_s"]
    events = [
        {
            "id": "counter:" + row["id"],
            "colour": row["colour"],
            "delivery_interval_s": [
                max(lo, row["evidence_interval_s"][0] - 15),
                min(hi, row["evidence_interval_s"][1] + 15),
            ],
            "counter_evidence_interval_s": row["evidence_interval_s"],
            "counter_update_s": row["crossing_time_s"],
        }
        for row in audit["counter_events"]
    ]
    result = {
        "source_id": audit["source_id"],
        "source_sha256": audit["source_sha256"],
        "source_interval_s": audit["source_interval_s"],
        "reference_method": "high_visibility_broadcast_counter_proxy",
        "audit_sha256": file_sha256(args.audit),
        "runner_sha256": file_sha256(__file__),
        "visible_fraction": audit["visible_sample_count"] / audit["sample_count"],
        "timing_expansion_s": [15, 15],
        "reference_limitations": [
            "A counter update can precede or follow visible stone movement; these are permissive proxy windows.",
            "The counter reader can flicker or miss a delivery even when the graphic is mostly readable.",
            "Counter concordance is not independent ground-truth throw F1 or release-time accuracy.",
        ],
        "events": events,
    }
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"proxy_events": len(events), "visible_fraction": result["visible_fraction"]}))


if __name__ == "__main__":
    main()
