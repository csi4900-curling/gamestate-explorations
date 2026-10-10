"""Apply frozen source-only transit-quality tie-break on end 7 or end 8."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from gate_transit_tiebreak import tiebreak_competing_transits

BASE = ROOT / "validation/curlobserver-learned-probe/cap-patch-crossmatch-v1"
CODE = ROOT / "prototype/gate_transit_tiebreak.py"


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("end", type=int, choices=(7, 8))
    args = parser.parse_args()
    end = args.end
    tag = "development" if end == 7 else "first"
    visual_path = BASE / f"norway-end{end}-dual-gate-first.json"
    routed_path = BASE / f"norway-end{end}-dual-gate-events-first.json"
    output_path = BASE / f"norway-end{end}-gate-tiebreak-events-{tag}.json"
    frozen_path = BASE / "norway-end7-gate-tiebreak-events-development.json"
    if output_path.exists():
        raise SystemExit("Output exists; preserve first result")
    visual, routed = (json.loads(path.read_text()) for path in
                      (visual_path, routed_path))
    if routed["visual_scan_sha256"] != digest(visual_path):
        raise ValueError("Visual scan changed after routing")
    if visual["source_sha256"] != routed["source_sha256"]:
        raise ValueError("Source mismatch")
    if end == 8:
        frozen = json.loads(frozen_path.read_text())
        if (frozen["tiebreak_code_sha256"] != digest(CODE)
                or frozen["source_sha256"] != routed["source_sha256"]):
            raise ValueError("Tie-break code or source changed after end seven")
    by_shot = {row["shot_id"]: row for row in visual["rows"]}
    decisions = [tiebreak_competing_transits(row, by_shot[row["shot_id"]])
                 for row in routed["decisions"]]
    changes = [row["shot_id"] for original, row in
               zip(routed["decisions"], decisions, strict=True)
               if row["colour"] != original["colour"]]
    output = {
        "status": f"source_only_end{end}_gate_tiebreak_{tag}",
        "source_sha256": routed["source_sha256"],
        "visual_scan_sha256": digest(visual_path),
        "routed_first_sha256": digest(routed_path),
        "tiebreak_code_sha256": digest(CODE),
        "runner_sha256": digest(Path(__file__)),
        "end": end,
        "origin_positive_count": len(decisions),
        "colour_resolved_count": sum(row["colour"] is not None for row in decisions),
        "changed_shot_ids": changes,
        "decisions": decisions,
        "limitations": [
            "The tie-break was selected after inspecting end-seven colour abstention.",
            "The end-seven result is postscore development, not validation.",
            "An early-gate observation is not a physical release timestamp.",
        ],
    }
    output_path.write_text(json.dumps(output, indent=2) + "\n")
    print({"end": end, "resolved": output["colour_resolved_count"],
           "changed_shot_ids": changes})


if __name__ == "__main__":
    main()
