"""Construct provisional throw review intervals with uncertainty preserved."""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cache_contract import file_sha256
from segment_passages import build_segments


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--events", type=Path, required=True)
    p.add_argument("--screen", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    if a.output.exists():
        p.error("Output exists; preserve earlier intervals")
    events = json.loads(a.events.read_text())
    screening = json.loads(a.screen.read_text())
    if screening["original_events_sha256"] != file_sha256(a.events):
        p.error("Screening does not match event artifact")
    start, end = events["source_interval_s"]
    payload = build_segments(events["events"], screening, start, end)
    result = {
        "status": "development_review_intervals_not_validated_throw_segments",
        "source_interval_s": [start, end],
        "events_sha256": file_sha256(a.events),
        "screen_sha256": file_sha256(a.screen),
        "builder_sha256": file_sha256(ROOT / "prototype/segment_passages.py"),
        **payload,
    }
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(
        json.dumps(
            {
                "review_intervals": len(payload["segments"]),
                "withheld": len(payload["withheld_candidates"]),
            }
        )
    )


if __name__ == "__main__":
    main()
