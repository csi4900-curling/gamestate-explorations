"""Find conservative continuous paths through far receiving-view candidates."""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cache_contract import file_sha256  # noqa: E402
from far_receiving_path import select_far_receiving_path  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scan", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Path artifact already exists")
    scan = json.loads(args.scan.read_text())
    if scan["status"] != "development_far_receiving_candidate_scan_not_identity_validation":
        parser.error("Unexpected scan status")
    rows = []
    for event in scan["rows"]:
        path = select_far_receiving_path(event)
        rows.append({"throw_id": event["throw_id"], "colour": event["colour"],
                     "departure_last": event["departure_last"],
                     "arrival_first": event["arrival_first"], **path})
    result = {
        "status": "development_cross_view_observation_paths_not_identity_validation",
        "source_clip_sha256": scan["source_clip_sha256"],
        "scan_sha256": file_sha256(args.scan),
        "path_code_sha256": file_sha256(ROOT / "prototype/far_receiving_path.py"),
        "runner_sha256": file_sha256(__file__),
        "throw_count": len(rows),
        "unique_path_count": sum(row["status"] ==
                                 "unique_maximum_coverage_path_provisional"
                                 for row in rows),
        "ambiguous_path_count": sum(row["status"] ==
                                    "multiple_maximum_coverage_paths"
                                    for row in rows),
        "unresolved_path_count": sum(row["status"] ==
                                     "no_endpoint_reaching_path"
                                     for row in rows),
        "rows": rows,
        "limitations": [
            "The path bounds were selected on exposed end-three development footage.",
            "Maximum-coverage continuity is not independent stone identity validation.",
            "Far-field metric accuracy and possible camera timing offset remain unvalidated.",
            "No points are interpolated and no physical release or settle time is inferred.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print({"unique": result["unique_path_count"],
           "ambiguous": result["ambiguous_path_count"],
           "unresolved": result["unresolved_path_count"]})


if __name__ == "__main__":
    main()
