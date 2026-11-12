"""Snapshot a fixed candidate range for source review while inference runs."""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from integrated_trajectory import reject_reused_tracks

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("directory", type=Path)
p.add_argument("start", type=int)
p.add_argument("end", type=int)
p.add_argument("output", type=Path)
a = p.parse_args()
files = [a.directory / "aggregate-events" / f"{i:04}.json" for i in range(a.start, a.end)]
rows = [json.loads(f.read_text()) for f in files]
if any(r["context"] != rows[0]["context"] for r in rows):
    raise ValueError("Mixed inference contexts")
events = [r["event"] for r in rows]
reject_reused_tracks(events)
a.output.write_text(
    json.dumps(
        {
            "context": rows[0]["context"],
            "events": events,
            "candidate_index_range": [a.start, a.end],
            "status": "partial review batch; final cross-event deconfliction can remove outputs, never add unchecked points",
        }
    )
    + "\n"
)
