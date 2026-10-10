"""Convert frozen outside-union source cues into explicit provisional rescue rows."""

from hashlib import sha256
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "validation/official-shot-sequence"
SCAN = BASE / "pwg2022-origin-shots-outside-union-cues-development.json"
UNION = BASE / "pwg2022-provisional-event-evidence-union-development.json"
PLAN = BASE / "pwg2022-origin-shots-outside-union-plan.json"
OUTPUT = BASE / "pwg2022-outside-union-release-rescue-proposals-development.json"


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def build():
    scan = json.loads(SCAN.read_text())
    union = json.loads(UNION.read_text())
    if scan["plan_sha256"] != digest(PLAN):
        raise ValueError("Scan does not match frozen shot selection")
    unions = {g["official_game_code"]: g for g in union["games"]}
    proposals = []
    for game in scan["games"]:
        code = game["recording_code"]
        current = unions[code]
        if game["source_sha256"] != current["source_sha256"]:
            raise ValueError("Source mismatch between scan and event union")
        used_shots = {sid for event in current["events"] for sid in event["source_shot_ids"]}
        for row in game["rows"]:
            if row["unique_supported_colour"] is None:
                continue
            if row["shot_id"] in used_shots or len(row["ice_supported_passages"]) != 1:
                raise ValueError("Rescue must be unique and outside union source shots")
            start, end = row["interval_s"]
            cue = row["ice_supported_passages"][0]
            if not start <= cue["held_interval_s"][0] < cue["release_cue_s"] < end:
                raise ValueError("Release cue outside camera shot")
            overlapping = [
                event["event_id"]
                for event in current["events"]
                if event["delivery_window_s"][0] < end and event["delivery_window_s"][1] > start
            ]
            if overlapping:
                raise ValueError(f"Rescue overlaps existing event windows: {overlapping}")
            proposals.append(
                {
                    "proposal_id": f"SOURCE-RELEASE-{code}-{row['shot_id']}",
                    "recording_code": code,
                    "source_sha256": game["source_sha256"],
                    "origin_shot_id": row["shot_id"],
                    "origin_shot_interval_s": row["interval_s"],
                    "origin_probability": row["origin_probability"],
                    "candidate_class": "source_only_held_release_provisional",
                    "release_cue_s": cue["release_cue_s"],
                    "observed_colour": cue["colour"],
                    "held_interval_s": cue["held_interval_s"],
                    "moving_interval_s": cue["moving_interval_s"],
                    "max_travel_px": cue["max_travel_px"],
                    "below_ice_fraction": cue["below_ice_fraction"],
                    "counter_id": None,
                    "official_shot_id": None,
                    "receiving_view_identity_verified": False,
                    "physical_throw_identity_verified": False,
                    "settled_board_transition_verified": False,
                    "simulation_ready": False,
                }
            )
    return {
        "status": "development_source_only_rescue_proposals_not_validated_physical_throws",
        "input_sha256": {
            "outside_union_scan": digest(SCAN),
            "frozen_selection": digest(PLAN),
            "provisional_union": digest(UNION),
            "runner": digest(Path(__file__)),
        },
        "proposal_count": len(proposals),
        "proposals": proposals,
        "limitations": [
            "The proposals have source-visible held-to-motion passages but no independently labeled physical throw identity.",
            "Neither proposal is merged into the frozen provisional event union or assigned an official shot number.",
            "No cross-view identity, settled board, or simulation-ready trajectory is established.",
        ],
    }


def main():
    payload = json.dumps(build(), indent=2) + "\n"
    if OUTPUT.exists() and OUTPUT.read_text() != payload:
        raise SystemExit("Existing rescue proposals differ from hashed source evidence")
    if not OUTPUT.exists():
        OUTPUT.write_text(payload)
    print(f"Verified {OUTPUT}")


if __name__ == "__main__":
    main()
