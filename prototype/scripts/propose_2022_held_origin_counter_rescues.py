"""Apply one held-origin recovery rule across three full 2022 recordings."""

from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from held_origin_counter_rescue import propose_held_origin_rescues

BASE = ROOT / "validation/official-shot-sequence"
ICE = BASE / "pwg2022-origin-release-ice-gate.json"
TRANSFER = BASE / "pwg2022-origin-release-transfer.json"
FUSED = {
    "PREL000101": ROOT / "validation/curlobserver-learned-probe/swiss-full-transfer/fused-cap.json",
    "PREL000102": ROOT
    / "validation/curlobserver-learned-probe/china-full-transfer/fused-shot-candidates-replay-cap.json",
    "PREL000103": ROOT
    / "validation/curlobserver-learned-probe/slovakia-full-transfer/fused-cap.json",
}
OUTPUT = BASE / "pwg2022-held-origin-counter-rescue-development.json"


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def build():
    ice = json.loads(ICE.read_text())
    transfer = json.loads(TRANSFER.read_text())
    if ice["transfer_sha256"] != digest(TRANSFER):
        raise ValueError("Held passage and ice gate provenance differ")
    reserved = json.loads((ROOT / "validation/unseen-end/reservation.json").read_text())
    games = []
    for code, path in FUSED.items():
        fused = json.loads(path.read_text())
        source = transfer["input_hashes_by_game"][code]["source_video_sha256"]
        if fused["source_sha256"] != source or source == reserved["source_sha256"]:
            raise ValueError(f"Source mismatch or reserved source selected: {code}")
        held = [row for row in ice["rows"] if row["official_game_code"] == code]
        result = propose_held_origin_rescues(fused, held)
        games.append(
            {
                "official_game_code": code,
                "source_sha256": source,
                "fused_sha256": digest(path),
                "existing_fused_event_count": fused["candidate_count"],
                "unassociated_counter_count": len(fused["unassociated_counter_events"]),
                "ice_gated_passage_count": sum(len(row["accepted_passages"]) for row in held),
                "provisional_rescue_count": len(result["proposals"]),
                "proposed_event_count_if_added": fused["candidate_count"]
                + len(result["proposals"]),
                **result,
            }
        )
    return {
        "status": "postscore_development_proposals_not_independent_throw_f1",
        "ice_gate_sha256": digest(ICE),
        "transfer_sha256": digest(TRANSFER),
        "join_code_sha256": digest(ROOT / "prototype/held_origin_counter_rescue.py"),
        "runner_sha256": digest(Path(__file__)),
        "rule": "For each unique ice-gated held-cap passage in an unused shot, require exactly one unused delayed counter of the same colour within 0–45 s of the release cue, and exactly one passage for that counter; otherwise abstain.",
        "games": games,
        "limitations": [
            "Held-cap thresholds and the ice gate were developed after inspecting these sources; this is not unseen evaluation.",
            "The counter is delayed and does not verify the held object as the delivered stone.",
            "Unmatched held passages are retained in the audit and are not promoted to events.",
            "The cap-fusion ledgers remain unchanged; proposed additions have no measured full-match physical precision or recall.",
        ],
    }


def main():
    payload = json.dumps(build(), indent=2) + "\n"
    if OUTPUT.exists():
        if OUTPUT.read_text() != payload:
            raise SystemExit("Existing rescue audit differs from current inputs or code")
        print(f"Verified {OUTPUT}")
    else:
        OUTPUT.write_text(payload)
        print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
