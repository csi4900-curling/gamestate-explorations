"""First source-separated transfer of the frozen ice-context tie-break."""

from hashlib import sha256
import json
from pathlib import Path
import sys

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from scripts.audit_2022_ambiguous_counter_ice_tiebreak import (
    MIN_MAX_CENTER_LOWER_ICE,
    MIN_ORIGIN_PROBABILITY,
    SAMPLE_FRACTIONS,
    select_unique_ice_supported,
)
from scripts.audit_candidate_ice_coverage import ice_fractions

BASE = ROOT / "validation/curlobserver-learned-probe/canada-norway-full-transfer"
ALIGNMENT = BASE / "counter-cap.json"
ORIGINS = BASE / "shot-origin.json"
VIDEO = ROOT / "validation/throw-event-benchmark/paralympics-2022-canada-norway/source.mp4"
PLAN = (
    ROOT / "validation/official-shot-sequence/norway-ambiguous-counter-ice-tiebreak-first-plan.json"
)
OUTPUT = ROOT / "validation/official-shot-sequence/norway-ambiguous-counter-ice-tiebreak-first.json"


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    if OUTPUT.exists():
        raise SystemExit("First transfer output exists; preserve it")
    plan = json.loads(PLAN.read_text())
    paths = {
        "rule_code": ROOT / "prototype/scripts/audit_2022_ambiguous_counter_ice_tiebreak.py",
        "ice_code": ROOT / "prototype/scripts/audit_candidate_ice_coverage.py",
        "counter_alignment": ALIGNMENT,
        "shot_origins": ORIGINS,
    }
    if {key: digest(path) for key, path in paths.items()} != plan["sha256"]:
        raise ValueError("Frozen plan inputs or rule changed")
    if (
        MIN_ORIGIN_PROBABILITY != plan["minimum_origin_probability"]
        or MIN_MAX_CENTER_LOWER_ICE != plan["minimum_max_center_lower_ice_fraction"]
        or list(SAMPLE_FRACTIONS) != plan["sample_fractions"]
    ):
        raise ValueError("Frozen rule parameters changed")
    alignment, origins = (json.loads(path.read_text()) for path in (ALIGNMENT, ORIGINS))
    source = plan["source_sha256"]
    reserved = json.loads((ROOT / "validation/unseen-end/reservation.json").read_text())
    if (
        source == reserved["source_sha256"]
        or alignment["source_sha256"] != source
        or origins["source_sha256"] != source
        or digest(VIDEO) != source
    ):
        raise ValueError("Video source does not match frozen plan")
    ambiguous = [
        row
        for row in alignment["rows"]
        if row["shot_id"] is None and len(row["candidate_shots"]) >= 2
    ]
    if [row["counter_id"] for row in ambiguous] != plan["selected_counter_ids"]:
        raise ValueError("Ambiguous counter set changed")
    capture = cv2.VideoCapture(str(VIDEO))
    if not capture.isOpened():
        raise RuntimeError("Cannot open Norway source")
    fps = capture.get(cv2.CAP_PROP_FPS)
    origin_by_shot = {row["shot_id"]: row for row in origins["rows"]}
    rows = []
    for counter in ambiguous:
        options = []
        for candidate in counter["candidate_shots"]:
            shot = origin_by_shot[candidate["shot_id"]]
            if shot["interval_s"] != candidate["interval_s"]:
                raise ValueError("Candidate and shot interval differ")
            start, end = shot["interval_s"]
            samples = []
            for fraction in SAMPLE_FRACTIONS:
                time_s = start + fraction * (end - start)
                capture.set(cv2.CAP_PROP_POS_FRAMES, round(time_s * fps))
                ok, frame = capture.read()
                if not ok:
                    raise RuntimeError(f"Frame decode failed at {time_s}")
                samples.append({"time_s": round(time_s, 3), "ice_fraction": ice_fractions(frame)})
            options.append(
                {
                    "shot_id": candidate["shot_id"],
                    "interval_s": shot["interval_s"],
                    "origin_probability": candidate["origin_probability"],
                    "max_center_lower_ice_fraction": max(
                        row["ice_fraction"]["center_lower"] for row in samples
                    ),
                    "samples": samples,
                }
            )
        selected = select_unique_ice_supported(options)
        rows.append(
            {
                "counter_id": counter["counter_id"],
                "counter_colour": counter["colour"],
                "counter_update_s": counter["counter_update_s"],
                "chosen_shot_id": selected,
                "status": "unique_ice_supported_option" if selected else "abstained",
                "options": options,
            }
        )
    capture.release()
    output = {
        "status": "first_norway_transfer_of_exposed_ice_tiebreak_not_event_f1",
        "source_sha256": source,
        "plan_sha256": digest(PLAN),
        "runner_sha256": digest(Path(__file__)),
        "ambiguous_counter_count": len(rows),
        "unique_ice_choice_count": sum(row["chosen_shot_id"] is not None for row in rows),
        "rows": rows,
        "limitations": [
            "The rule was developed after inspecting Swiss B70; Norway tests source separation, not independent physical truth.",
            "One ambiguous counter cannot establish transfer precision or recall.",
            "No event candidate, counter assignment or throw count was changed.",
        ],
    }
    OUTPUT.write_text(json.dumps(output, indent=2) + "\n")
    print({"ambiguous": len(rows), "chosen": output["unique_ice_choice_count"]})


if __name__ == "__main__":
    main()
