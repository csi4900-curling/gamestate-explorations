"""Compare phase-aware v2 fallback with preserved v1 first-transfer outputs."""

from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from nonorigin_continuity_rescue_v2 import rescue_phase_supported_nonorigin_shots

BASE = ROOT / "validation/curlobserver-learned-probe"
STUDY = BASE / "cap-patch-crossmatch-v1"
OUTPUT = STUDY / "nonorigin-phase-v2-development.json"
CASES = (
    ("norway-end7", "canada-norway-full-transfer",
     "norway-end7-nonorigin-continuity-development.json"),
    ("norway-end8", "canada-norway-full-transfer",
     "norway-end8-nonorigin-continuity-first.json"),
    ("slovakia", "slovakia-full-transfer",
     "slovakia-nonorigin-continuity-first.json"),
    ("swiss", "swiss-full-transfer",
     "swiss-nonorigin-continuity-first.json"),
)


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    if OUTPUT.exists():
        raise SystemExit("Output exists; preserve first v2 development audit")
    reserved = json.loads((ROOT / "validation/unseen-end/reservation.json").read_text())
    results = []
    for name, folder, prior_file in CASES:
        cap_path = BASE / folder / "cap-motion.json"
        origin_path = BASE / folder / "shot-origin.json"
        prior_path = STUDY / prior_file
        cap, origin, prior = (json.loads(path.read_text()) for path in
                              (cap_path, origin_path, prior_path))
        if not (cap["source_sha256"] == origin["source_sha256"] ==
                prior["source_sha256"]):
            raise ValueError("Source mismatch")
        if cap["source_sha256"] == reserved["source_sha256"]:
            raise ValueError("Reserved independent source is not development data")
        if (prior["cap_motion_sha256"] != digest(cap_path) or
                prior["shot_origin_sha256"] != digest(origin_path)):
            raise ValueError("Preserved v1 input changed")
        by_id = {row["shot_id"]: row for row in origin["rows"]}
        interval = prior["interval_s"] if "interval_s" in prior else prior["source_interval_s"]
        candidates = rescue_phase_supported_nonorigin_shots(cap["shots"], by_id, interval)
        prior_ids = {row["shot_id"] for row in prior["candidates"]}
        new_ids = {row["shot_id"] for row in candidates}
        result = {"case": name, "source_sha256": cap["source_sha256"],
                  "prior_sha256": digest(prior_path),
                  "cap_motion_sha256": digest(cap_path),
                  "shot_origin_sha256": digest(origin_path),
                  "v1_count": len(prior_ids), "v2_count": len(new_ids),
                  "removed_shot_ids": sorted(prior_ids - new_ids),
                  "added_shot_ids": sorted(new_ids - prior_ids),
                  "candidates": candidates}
        results.append(result)
        print(name, {key: result[key] for key in
                     ("v1_count", "v2_count", "removed_shot_ids", "added_shot_ids")})
    output = {
        "status": "postscore_phase_veto_development_not_independent_transfer",
        "v1_code_sha256": digest(ROOT / "prototype/nonorigin_continuity_rescue.py"),
        "v2_code_sha256": digest(ROOT / "prototype/nonorigin_continuity_rescue_v2.py"),
        "runner_sha256": digest(Path(__file__)),
        "cases": results,
        "limitations": [
            "The phase requirement was added after seeing false positives in Swiss source frames.",
            "Existing frozen phase labels may miss true deliveries, so recall is unmeasured.",
            "No independent physical throw reference is used.",
        ],
    }
    OUTPUT.write_text(json.dumps(output, indent=2) + "\n")


if __name__ == "__main__":
    main()
