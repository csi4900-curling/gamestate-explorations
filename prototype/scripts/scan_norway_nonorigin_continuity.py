"""Source-only non-origin stone-motion rescue, end-7 development/end-8 first."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from nonorigin_continuity_rescue import rescue_nonorigin_shots

BASE = ROOT / "validation/curlobserver-learned-probe/canada-norway-full-transfer"
STUDY = ROOT / "validation/curlobserver-learned-probe/cap-patch-crossmatch-v1"
SHOTS = BASE / "cap-motion.json"
ORIGINS = BASE / "shot-origin.json"
CODE = ROOT / "prototype/nonorigin_continuity_rescue.py"
INTERVALS = {7: (6364.3, 7372.1), 8: (7372.1, 9039.0)}


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("end", type=int, choices=(7, 8))
    args = parser.parse_args()
    end = args.end
    tag = "development" if end == 7 else "first"
    output_path = STUDY / f"norway-end{end}-nonorigin-continuity-{tag}.json"
    if output_path.exists():
        raise SystemExit("Output exists; preserve first result")
    shots, origins = (json.loads(path.read_text()) for path in (SHOTS, ORIGINS))
    if shots["source_sha256"] != origins["source_sha256"]:
        raise ValueError("Source mismatch")
    if end == 8:
        frozen_path = STUDY / "norway-end7-nonorigin-continuity-development.json"
        frozen = json.loads(frozen_path.read_text())
        if (frozen["rescue_code_sha256"] != digest(CODE) or
                frozen["source_sha256"] != shots["source_sha256"]):
            raise ValueError("Rescue code or source changed after end seven")
    reserved = json.loads((ROOT / "validation/unseen-end/reservation.json").read_text())
    if shots["source_sha256"] == reserved["source_sha256"]:
        raise ValueError("Reserved independent source is not development data")
    origin_by_id = {row["shot_id"]: row for row in origins["rows"]}
    candidates = rescue_nonorigin_shots(shots["shots"], origin_by_id,
                                        INTERVALS[end])
    output = {
        "status": f"source_only_end{end}_nonorigin_continuity_{tag}",
        "source_sha256": shots["source_sha256"],
        "cap_motion_sha256": digest(SHOTS),
        "shot_origin_sha256": digest(ORIGINS),
        "rescue_code_sha256": digest(CODE),
        "runner_sha256": digest(Path(__file__)),
        "end": end,
        "interval_s": list(INTERVALS[end]),
        "candidate_count": len(candidates),
        "candidates": candidates,
        "limitations": [
            "Criteria were selected after inspecting an end-seven miss.",
            "Cap tracks can include non-stone pixels and duplicate an earlier event.",
            "Same colour in adjacent views does not prove physical identity.",
            "The candidate interval is a camera shot, not an exact throw boundary.",
        ],
    }
    output_path.write_text(json.dumps(output, indent=2) + "\n")
    print({"end": end, "candidates": [(row["shot_id"], row["colour"])
                                      for row in candidates]})


if __name__ == "__main__":
    main()
