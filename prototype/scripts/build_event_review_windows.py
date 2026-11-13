"""Build uncertainty-preserving review windows from a throw-event artifact."""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cache_contract import file_sha256
from event_review_windows import build_review_windows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--events", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--before-s", type=float, default=20.0)
    parser.add_argument("--after-s", type=float, default=45.0)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists; preserve previous review windows")
    source = json.loads(args.events.read_text())
    payload = build_review_windows(
        source["events"],
        source["source_interval_s"],
        before_s=args.before_s,
        after_s=args.after_s,
    )
    result = {
        "status": "development_review_windows_not_physical_shot_segments",
        "source_id": source["source_id"],
        "source_sha256": source["source_sha256"],
        "event_artifact_sha256": file_sha256(args.events),
        "builder_sha256": file_sha256(ROOT / "prototype/event_review_windows.py"),
        **payload,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"review_windows": len(payload["review_windows"])}))


if __name__ == "__main__":
    main()
