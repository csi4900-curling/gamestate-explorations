"""Check whether source-yellow S593 resolves China end-eight sequence ambiguity."""

from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from prototype.official_candidate_sequence import align_official_sequence

BASE = ROOT / "validation/official-shot-sequence"
SEQUENCE = BASE / "pwg2022-v3-official-sequence-diagnostic-development.json"
UNION = BASE / "pwg2022-provisional-event-evidence-union-v3-preorigin-travel-development.json"
COUNTERS = BASE / "pwg2022-official-counter-alignment.json"
REFERENCE = BASE / "pwg2022-official-shot-ledger.json"
HANDOFF = BASE / "pwg2022-event-evidence-handoff-v3-development.json"
OUTPUT = BASE / "china-s593-sequence-colour-sensitivity-development.json"


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def find(rows, key, value):
    selected = [row for row in rows if row[key] == value]
    if len(selected) != 1:
        raise ValueError(f"Expected one {key}={value}")
    return selected[0]


def build():
    sequence = json.loads(SEQUENCE.read_text())
    union = json.loads(UNION.read_text())
    counters = json.loads(COUNTERS.read_text())
    reference = json.loads(REFERENCE.read_text())
    handoff = json.loads(HANDOFF.read_text())
    code = "PREL000102"
    audited = find(sequence["games"], "recording_code", code)
    end_audit = find(audited["ends"], "end", 8)
    game = find(union["games"], "official_game_code", code)
    counter_game = find(counters["games"], "official_game_code", code)
    official = find(reference["games"], "official_game_code", code)
    end = find(official["ends"], "end", 8)
    evidence = find(find(handoff["games"], "recording_code", code)["rows"],
                    "event_id", "VISUAL-S593")
    if (game["source_sha256"] != official["source_video_sha256"] or
            evidence["event_colour"] != "red" or
            evidence["release_cue"]["colour"] != "yellow" or
            evidence["receiving_view"]["colour"] != "yellow" or
            evidence["receiving_view"]["status"] !=
            "source_colour_concordant_identity_unverified" or
            evidence["receiving_view"]["physical_stone_identity_verified"]):
        raise ValueError("S593 source-colour evidence changed")
    event_by_id = {row["event_id"]: row for row in game["events"]}
    counter_by_id = {row["counter_id"]: row for row in counter_game["counter_rows"]}
    candidate_ids = [row["candidate_id"] for row in end_audit["candidate_rows"]]
    candidates = [{"candidate_id": event_id,
                   "colour": event_by_id[event_id]["colour"]}
                  for event_id in candidate_ids]
    fixed = {}
    for event_id in candidate_ids:
        event = event_by_id[event_id]
        if event["counter_id"] is None:
            continue
        counter = counter_by_id[event["counter_id"]]
        if (counter["status"] == "unique_colour_concordant" and
                counter["official_shot_id"] is not None and
                event["colour"] == counter["official_colour"]):
            fixed[event_id] = counter["official_shot_id"]
    baseline = align_official_sequence(
        candidates, end["shots"], official["team_handle_colours"], fixed)
    if (baseline["candidate_rows"] != end_audit["candidate_rows"] or
            baseline["official_rows"] != end_audit["official_rows"] or
            baseline["minimum_cost"] != end_audit["minimum_edit_cost"]):
        raise ValueError("Recomputed baseline differs from frozen v3 sequence audit")
    corrected = [dict(row, colour="yellow") if row["candidate_id"] == "VISUAL-S593"
                 else row for row in candidates]
    scenario = align_official_sequence(
        corrected, end["shots"], official["team_handle_colours"], fixed)
    return {"status": "development_source_colour_sequence_sensitivity_not_physical_identity",
            "event_id": "VISUAL-S593", "recording_code": code, "end": 8,
            "input_sha256": {"v3_sequence": digest(SEQUENCE), "v3_union": digest(UNION),
                             "counter_alignment": digest(COUNTERS),
                             "official_reference": digest(REFERENCE),
                             "v3_evidence_handoff": digest(HANDOFF),
                             "alignment_code": digest(ROOT / "prototype/official_candidate_sequence.py"),
                             "runner": digest(Path(__file__))},
            "source_evidence": {"event_ledger_colour": "red",
                                "within_view_release_cue_colour": "yellow",
                                "receiving_view_colour": "yellow",
                                "physical_stone_identity_verified": False},
            "fixed_counter_anchor_count": len(fixed),
            "baseline": baseline,
            "source_yellow_scenario": scenario,
            "limitations": [
                "The official shot list and counter anchors are used only for this postscore sequence sensitivity audit.",
                "The same-colour source cues do not verify persistent physical stone identity across the broadcast cut.",
                "A lower sequence edit cost is not independent physical event or colour accuracy and does not change the frozen union.",
            ]}


def main():
    payload = json.dumps(build(), indent=2) + "\n"
    if OUTPUT.exists() and OUTPUT.read_text() != payload:
        raise SystemExit("Existing S593 sensitivity differs from hashed inputs")
    if not OUTPUT.exists():
        OUTPUT.write_text(payload)
    print(f"Verified {OUTPUT}")


if __name__ == "__main__":
    main()
