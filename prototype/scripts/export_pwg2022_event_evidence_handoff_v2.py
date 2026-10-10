"""Export one provenance-preserving event-to-board handoff for the v2 union."""

from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from prototype.event_evidence_handoff_v2 import join_event_evidence

BASE = ROOT / "validation/official-shot-sequence"
INPUTS = {
    "union": BASE / "pwg2022-provisional-event-evidence-union-v2-source-rescues-development.json",
    "shot_scoped_release": BASE / "pwg2022-shot-scoped-release-cues-development.json",
    "baseline_crossview": BASE / "pwg2022-cross-view-source-colour-handoff-development.json",
    "rescue_proposals": BASE / "pwg2022-outside-union-release-rescue-proposals-development.json",
    "rescue_receiving": BASE / "pwg2022-outside-union-receiving-view-development.json",
    "partial_boards": BASE / "pwg2022-held-shot-release-to-board-development.json",
    "review_segments": BASE
    / "pwg2022-full-match-event-review-segments-v2-source-rescues-development.json",
}
OUTPUT = BASE / "pwg2022-event-evidence-handoff-v2-development.json"


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def by_code(games, key):
    index = {game[key]: game for game in games}
    if len(index) != len(games):
        raise ValueError("Duplicate recording code")
    return index


def build():
    data = {key: json.loads(path.read_text()) for key, path in INPUTS.items()}
    union = data["union"]
    releases = by_code(data["shot_scoped_release"]["games"], "recording_code")
    crossviews = by_code(data["baseline_crossview"]["games"], "recording_code")
    reviews = by_code(data["review_segments"]["games"], "official_game_code")
    reserved = json.loads((ROOT / "validation/unseen-end/reservation.json").read_text())
    boards = data["partial_boards"]["rows"]
    proposals = data["rescue_proposals"]["proposals"]
    receiving = data["rescue_receiving"]["rows"]
    games = []
    for game in union["games"]:
        code = game["official_game_code"]
        source = game["source_sha256"]
        if (
            source == reserved["source_sha256"]
            or releases[code]["source_sha256"] != source
            or crossviews[code]["source_sha256"] != source
            or reviews[code]["source_sha256"] != source
        ):
            raise ValueError("Event handoff source mismatch or reserved-source overlap")
        local_boards = [row for row in boards if row["source_recording_code"] == code]
        if any(row["source_video_sha256"] != source for row in local_boards):
            raise ValueError("Partial board source mismatch")
        local_proposals = [row for row in proposals if row["recording_code"] == code]
        local_receiving = [row for row in receiving if row["recording_code"] == code]
        if any(row["source_sha256"] != source for row in local_proposals):
            raise ValueError("Rescue proposal source mismatch")
        rows = join_event_evidence(
            game["events"],
            releases[code]["rows"],
            crossviews[code]["rows"],
            local_proposals,
            local_receiving,
            local_boards,
            reviews[code]["segments"],
        )
        if len(rows) != game["provisional_event_count"]:
            raise ValueError("Event count changed in evidence handoff")
        games.append(
            {
                "recording_code": code,
                "source_sha256": source,
                "event_count": len(rows),
                "unique_release_cue_count": sum(
                    row["release_cue"]["time_s"] is not None for row in rows
                ),
                "two_view_source_colour_agreement_count": sum(
                    row["receiving_view"]["status"]
                    == "source_colour_concordant_identity_unverified"
                    for row in rows
                ),
                "partial_board_link_count": sum(len(row["partial_board_links"]) for row in rows),
                "release_cue_and_partial_board_count": sum(
                    row["release_cue"]["time_s"] is not None and bool(row["partial_board_links"])
                    for row in rows
                ),
                "rows": rows,
            }
        )
    return {
        "status": "development_v2_event_evidence_handoff_not_simulation_ready",
        "input_sha256": {
            **{key: digest(path) for key, path in INPUTS.items()},
            "join_code": digest(ROOT / "prototype/event_evidence_handoff_v2.py"),
            "runner": digest(Path(__file__)),
        },
        "event_count": sum(game["event_count"] for game in games),
        "unique_release_cue_count": sum(game["unique_release_cue_count"] for game in games),
        "two_view_source_colour_agreement_count": sum(
            game["two_view_source_colour_agreement_count"] for game in games
        ),
        "partial_board_link_count": sum(game["partial_board_link_count"] for game in games),
        "release_cue_and_partial_board_count": sum(
            game["release_cue_and_partial_board_count"] for game in games
        ),
        "games": games,
        "limitations": [
            "Release cues are approximate visible held-to-motion times, not exact physical releases.",
            "Same-colour receiving-view motion does not verify persistent stone identity across a cut.",
            "Board links use delayed counter bookkeeping, not a verified physical state transition.",
            "Every board is partial and uncalibrated; no event has a simulation-ready trajectory or state.",
            "The 358 candidates are development outputs without independent complete-match physical throw F1.",
        ],
    }


def main():
    payload = json.dumps(build(), indent=2) + "\n"
    if OUTPUT.exists() and OUTPUT.read_text() != payload:
        raise SystemExit("Existing v2 evidence handoff differs from hashed inputs")
    if not OUTPUT.exists():
        OUTPUT.write_text(payload)
    print(f"Verified {OUTPUT}")


if __name__ == "__main__":
    main()
