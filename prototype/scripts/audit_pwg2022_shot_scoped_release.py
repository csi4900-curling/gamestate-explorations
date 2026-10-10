"""Build a shot-scoped release ledger from frozen candidate and source evidence."""

from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from prototype.shot_scoped_release import select_event_release

BASE = ROOT / "validation/official-shot-sequence"
UNION = BASE / "pwg2022-provisional-event-evidence-union-development.json"
HELD = BASE / "pwg2022-held-shot-release-to-board-development.json"
RELEASES = {
    "PREL000101": BASE / "swiss-provisional-release-transfer-first.json",
    "PREL000102": BASE / "china-provisional-release-transfer-first.json",
    "PREL000103": BASE / "slovakia-provisional-release-coverage-development.json",
}
SHOTS = {
    "PREL000101": ROOT
    / "validation/curlobserver-learned-probe/swiss-full-transfer/shot-origin.json",
    "PREL000102": ROOT
    / "validation/curlobserver-learned-probe/china-full-transfer/unlabelled-shot-origin-inference.json",
    "PREL000103": ROOT
    / "validation/curlobserver-learned-probe/slovakia-full-transfer/shot-origin.json",
}
OUTPUT = BASE / "pwg2022-shot-scoped-release-cues-development.json"


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def build():
    union = json.loads(UNION.read_text())
    held = json.loads(HELD.read_text())
    held_scans = {row["event_id"]: row for row in held["rescanned_held_origin_shots"]}
    reserved = json.loads((ROOT / "validation/unseen-end/reservation.json").read_text())
    games = []
    for game in union["games"]:
        code = game["official_game_code"]
        release = json.loads(RELEASES[code].read_text())
        shots = json.loads(SHOTS[code].read_text())
        if (
            game["source_sha256"] != release["source_sha256"]
            or game["source_sha256"] != shots["source_sha256"]
            or game["source_sha256"] == reserved["source_sha256"]
        ):
            raise ValueError("Event, release and shot sources differ or include reserved source")
        release_by_event = {row["event_id"]: row for row in release["rows"]}
        shot_by_id = {row["shot_id"]: row["interval_s"] for row in shots["rows"]}
        if len(release_by_event) != len(release["rows"]) or len(shot_by_id) != len(shots["rows"]):
            raise ValueError("Duplicate event or shot ID")
        if set(release_by_event) != {event["event_id"] for event in game["events"]}:
            raise ValueError("Event and release ledgers differ")
        rows = []
        for event in game["events"]:
            original = release_by_event[event["event_id"]]
            decision = select_event_release(event, original, shot_by_id, held_scans)
            colour = decision["unique_passage_colour"]
            ledger = event["colour"]
            rows.append(
                {
                    "event_id": event["event_id"],
                    "candidate_class": event["candidate_class"],
                    "source_shot_ids": event["source_shot_ids"],
                    "counter_id": event["counter_id"],
                    "ledger_colour": ledger,
                    "broad_scan_unique_release_cue_s": original["unique_release_cue_s"],
                    **decision,
                    "colour_relation": (
                        "no_unique_passage"
                        if colour is None
                        else "ledger_colour_unknown"
                        if ledger is None
                        else "agrees_with_ledger"
                        if colour == ledger
                        else "conflicts_with_ledger"
                    ),
                    "physical_stone_identity_verified": False,
                    "simulation_ready": False,
                }
            )
        games.append(
            {
                "recording_code": code,
                "source_sha256": game["source_sha256"],
                "provisional_event_count": len(rows),
                "unique_scoped_cue_count": sum(
                    row["unique_release_cue_s"] is not None for row in rows
                ),
                "unscoped_travel_abstention_count": sum(
                    row["scope_status"] == "no_attached_origin_shot" for row in rows
                ),
                "rows": rows,
            }
        )
    return {
        "status": "development_shot_scoped_release_cue_coverage_not_throw_f1",
        "input_sha256": {
            "union": digest(UNION),
            "held_shot_rescan": digest(HELD),
            "releases": {k: digest(v) for k, v in RELEASES.items()},
            "shot_tables": {k: digest(v) for k, v in SHOTS.items()},
            "selection_code": digest(ROOT / "prototype/shot_scoped_release.py"),
            "runner": digest(Path(__file__)),
        },
        "provisional_event_count": sum(game["provisional_event_count"] for game in games),
        "unique_scoped_cue_count": sum(game["unique_scoped_cue_count"] for game in games),
        "games": games,
        "limitations": [
            "Shot scope prevents assigning a passage from an unrelated camera shot to a travel-only candidate.",
            "The scoped ledger reuses previous candidate-window scans except for two source-rescanned attached held-origin shots.",
            "Candidate cue coverage is not independently measured physical throw precision, recall or F1.",
            "No cross-view physical stone identity, settled-board transition or simulation-ready state is verified.",
        ],
    }


def main():
    payload = json.dumps(build(), indent=2) + "\n"
    if OUTPUT.exists() and OUTPUT.read_text() != payload:
        raise SystemExit("Existing scoped cue ledger differs from hashed inputs or code")
    if not OUTPUT.exists():
        OUTPUT.write_text(payload)
    print(f"Verified {OUTPUT}")


if __name__ == "__main__":
    main()
