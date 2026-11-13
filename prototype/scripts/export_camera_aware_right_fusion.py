"""Export camera-aware right-entry review statuses without accepting new throws."""

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from camera_aware_right_fusion import fuse


def digest(path):
    h = sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--right", type=Path, required=True)
    parser.add_argument("--left", type=Path, required=True)
    parser.add_argument("--coverage", type=Path, required=True)
    parser.add_argument("--partial-state", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists")
    right = json.loads(args.right.read_text())
    left = json.loads(args.left.read_text())
    coverage = json.loads(args.coverage.read_text())
    state = json.loads(args.partial_state.read_text()) if args.partial_state else None
    rows = fuse(right, left, coverage, partial_state=state)
    counts = Counter(row["fusion_status"] for row in rows)
    result = {
        "status": "camera_aware_right_entry_development_review_not_accepted_throw_timeline",
        "source_sha256": right["source_sha256"],
        "right_sha256": digest(args.right),
        "left_sha256": digest(args.left),
        "coverage_sha256": digest(args.coverage),
        "partial_state_sha256": digest(args.partial_state) if args.partial_state else None,
        "fusion_code_sha256": digest(ROOT / "prototype/camera_aware_right_fusion.py"),
        "runner_sha256": digest(Path(__file__)),
        "maximum_left_before_right_lag_s": 20,
        "right_entry_count": len(rows),
        "fusion_status_counts": dict(counts),
        "right_entries": rows,
        "limitations": [
            "A time/colour corroboration does not prove physical stone identity.",
            "Right-only entries during left-camera blindness are review proposals, not accepted throws.",
            "A supported layout run can contain shorter hidden camera changes.",
            "No precision, recall or F1 is estimated from these exposed development artifacts.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"right_entries": len(rows), "statuses": dict(counts)}))


if __name__ == "__main__":
    main()
