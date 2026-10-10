"""Develop source-only mirrored-gate routing on exposed ends four and five."""

from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from dual_departure_gate import route_gate_sides

BASE = ROOT / "validation/curlobserver-learned-probe/cap-patch-crossmatch-v1"
INPUTS = {
    4: (BASE / "norway-end4-left-gate-development.json",
        BASE / "norway-end4-departure-gate-development.json"),
    5: (BASE / "norway-end5-left-gate-development.json",
        BASE / "norway-end5-departure-gate-first.json"),
}
OUTPUT = BASE / "norway-end4-end5-dual-gate-development.json"


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    if OUTPUT.exists():
        raise SystemExit("Output exists; preserve first dual-gate development result")
    paired = []
    hashes = {}
    source_hash = None
    for end, (left_path, right_path) in INPUTS.items():
        left, right = (json.loads(path.read_text()) for path in (left_path, right_path))
        if left["source_sha256"] != right["source_sha256"]:
            raise ValueError("Left and right gates have different videos")
        if source_hash is None:
            source_hash = left["source_sha256"]
        elif source_hash != left["source_sha256"]:
            raise ValueError("End sources differ")
        if [row["shot_id"] for row in left["rows"]] != [row["shot_id"] for row in right["rows"]]:
            raise ValueError("Left/right origin shots differ")
        hashes[str(end)] = {"left": digest(left_path), "right": digest(right_path)}
        for lrow, rrow in zip(left["rows"], right["rows"]):
            if lrow["interval_s"] != rrow["interval_s"]:
                raise ValueError("Left/right camera interval differs")
            paired.append({"shot_id": lrow["shot_id"],
                           "interval_s": lrow["interval_s"],
                           "left": lrow, "right": rrow})
    decisions = route_gate_sides(paired)
    result = {
        "status": "postscore_exposed_end4_end5_dual_gate_orientation_development",
        "source_sha256": source_hash,
        "input_sha256_by_end": hashes,
        "router_code_sha256": digest(ROOT / "prototype/dual_departure_gate.py"),
        "colour_code_sha256": digest(ROOT / "prototype/departure_gate_decision.py"),
        "runner_sha256": digest(Path(__file__)),
        "origin_positive_count": len(decisions),
        "colour_resolved_count": sum(row["colour"] is not None for row in decisions),
        "decisions": decisions,
        "limitations": [
            "Router was designed after viewing end-four and end-five failures and gate counts.",
            "Motion points can come from an old stone or a broadcast camera move; orientation is provisional.",
            "No official sequence or counter colour enters the routing function.",
        ],
    }
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n")
    for row in decisions:
        print(row["shot_id"], row["side"], row["colour"], row["side_route"])


if __name__ == "__main__":
    main()
