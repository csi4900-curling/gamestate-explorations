"""First full-China source-only transfer of the frozen phase-aware fallback."""

from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from nonorigin_continuity_rescue_v2 import rescue_phase_supported_nonorigin_shots

BASE = ROOT / "validation/curlobserver-learned-probe/china-full-transfer"
STUDY = ROOT / "validation/curlobserver-learned-probe/cap-patch-crossmatch-v1"
CAP = BASE / "sequential-shot-cap-motion.json"
ORIGIN = BASE / "unlabelled-shot-origin-inference.json"
PLAN = STUDY / "china-nonorigin-phase-v2-first-plan.json"
OUTPUT = STUDY / "china-nonorigin-phase-v2-first.json"


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    if OUTPUT.exists():
        raise SystemExit("Output exists; preserve first China v2 transfer")
    plan = json.loads(PLAN.read_text())
    files = {"cap_motion": CAP, "origin": ORIGIN,
             "phase_v2_code": ROOT / "prototype/nonorigin_continuity_rescue_v2.py",
             "base_rescue_code": ROOT / "prototype/nonorigin_continuity_rescue.py",
             "runner": Path(__file__)}
    hashes = {name: digest(path) for name, path in files.items()}
    if hashes != plan["frozen_sha256"]:
        raise ValueError("Frozen source-only input or code changed")
    cap, origin = (json.loads(path.read_text()) for path in (CAP, ORIGIN))
    if (cap["source_sha256"] != origin["source_sha256"] or
            cap["source_interval_s"] != origin["source_interval_s"] or
            cap["source_interval_s"] != plan["source_interval_s"] or
            len(cap["shots"]) != plan["shot_count"] or
            len(origin["rows"]) != plan["shot_count"]):
        raise ValueError("Source interval or shot inventory changed")
    reserved = json.loads((ROOT / "validation/unseen-end/reservation.json").read_text())
    if cap["source_sha256"] == reserved["source_sha256"]:
        raise ValueError("Reserved independent source selected")
    origins = {row["shot_id"]: row for row in origin["rows"]}
    if (len(origins) != len(origin["rows"]) or
            set(origins) != {shot["shot_id"] for shot in cap["shots"]}):
        raise ValueError("Shot IDs differ across source-only inputs")
    candidates = rescue_phase_supported_nonorigin_shots(
        cap["shots"], origins, cap["source_interval_s"])
    output = {
        "status": "first_full_china_source_only_phase_v2_nonorigin_transfer",
        "source_sha256": cap["source_sha256"],
        "source_interval_s": cap["source_interval_s"],
        "plan_sha256": digest(PLAN),
        "frozen_sha256": hashes,
        "shot_count": len(cap["shots"]),
        "candidate_count": len(candidates),
        "candidates": candidates,
        "limitations": [
            "The phase-aware rule was developed after Norway and Swiss results, before this China run.",
            "China was exposed in earlier project work but not used to fit this fallback.",
            "Cap motion and origin phase can both be wrong; adjacent same-colour tracks do not prove stone identity.",
            "This is not an exhaustive event detector or a physical throw precision/recall score.",
            "No counter colour, official shot order or reserved source is used for candidate generation.",
        ],
    }
    OUTPUT.write_text(json.dumps(output, indent=2) + "\n")
    print({"shots": len(cap["shots"]), "candidates": len(candidates),
           "items": [(row["shot_id"], row["colour"], row["interval_s"])
                     for row in candidates]})


if __name__ == "__main__":
    main()
