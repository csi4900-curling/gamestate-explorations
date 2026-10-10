"""Create coverage-clipped review windows from a partial throw timeline."""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cache_contract import file_sha256
from timeline_review_windows import build_timeline_review_windows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timeline", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--before-s", type=float, default=20)
    parser.add_argument("--after-s", type=float, default=45)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists; preserve previous review windows")
    source = json.loads(args.timeline.read_text())
    if source.get("status") not in ("partial_coverage", "sampled_layout_coverage"):
        parser.error("Input is not a routed partial timeline")
    result = build_timeline_review_windows(
        source,
        before_s=args.before_s,
        after_s=args.after_s,
    )
    result["timeline_sha256"] = file_sha256(args.timeline)
    result["builder_sha256"] = file_sha256(ROOT / "prototype/timeline_review_windows.py")
    result["runner_sha256"] = file_sha256(__file__)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"review_windows": result["review_window_count"]}))


if __name__ == "__main__":
    main()
