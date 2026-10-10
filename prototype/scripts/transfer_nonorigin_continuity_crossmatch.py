"""First source-only cross-recording transfer of frozen non-origin rescue."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from nonorigin_continuity_rescue import rescue_nonorigin_shots

BASE = ROOT / "validation/curlobserver-learned-probe"
STUDY = BASE / "cap-patch-crossmatch-v1"
CODE = ROOT / "prototype/nonorigin_continuity_rescue.py"
FROZEN = STUDY / "norway-end7-nonorigin-continuity-development.json"
SOURCES = {"slovakia": "slovakia-full-transfer", "swiss": "swiss-full-transfer"}


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source", choices=tuple(SOURCES))
    args = parser.parse_args()
    folder = BASE / SOURCES[args.source]
    cap_path, origin_path = folder / "cap-motion.json", folder / "shot-origin.json"
    output_path = STUDY / f"{args.source}-nonorigin-continuity-first.json"
    if output_path.exists():
        raise SystemExit("Output exists; preserve first transfer")
    cap, origin, frozen = (json.loads(path.read_text()) for path in (cap_path, origin_path, FROZEN))
    if cap["source_sha256"] != origin["source_sha256"]:
        raise ValueError("Source mismatch")
    if frozen["rescue_code_sha256"] != digest(CODE):
        raise ValueError("Rescue rule changed after development")
    reserved = json.loads((ROOT / "validation/unseen-end/reservation.json").read_text())
    if cap["source_sha256"] == reserved["source_sha256"]:
        raise ValueError("Reserved independent source is not development data")
    if cap["source_interval_s"] != origin["source_interval_s"]:
        raise ValueError("Source intervals differ")
    by_id = {row["shot_id"]: row for row in origin["rows"]}
    candidates = rescue_nonorigin_shots(cap["shots"], by_id, cap["source_interval_s"])
    output = {
        "status": "first_crossmatch_source_only_nonorigin_continuity_transfer",
        "source": args.source,
        "source_sha256": cap["source_sha256"],
        "source_interval_s": cap["source_interval_s"],
        "cap_motion_sha256": digest(cap_path),
        "shot_origin_sha256": digest(origin_path),
        "frozen_end7_sha256": digest(FROZEN),
        "rescue_code_sha256": digest(CODE),
        "runner_sha256": digest(Path(__file__)),
        "candidate_count": len(candidates),
        "candidates": candidates,
        "limitations": [
            "No independent throw labels or complete physical event score are used.",
            "Same-colour adjacent-view cap motion does not prove one stone identity.",
            "This is an unpromoted rescue candidate list, not a full event detector.",
        ],
    }
    output_path.write_text(json.dumps(output, indent=2) + "\n")
    print(
        args.source,
        output["candidate_count"],
        [(row["shot_id"], row["colour"], row["interval_s"]) for row in candidates],
    )


if __name__ == "__main__":
    main()
