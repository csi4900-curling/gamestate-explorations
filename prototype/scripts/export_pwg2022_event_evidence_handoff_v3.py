"""Extend the 358-event handoff with B02 receiving travel and no release cue."""

from hashlib import sha256
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "validation/official-shot-sequence"
V2 = BASE / "pwg2022-event-evidence-handoff-v2-development.json"
UNION = BASE / "pwg2022-provisional-event-evidence-union-v3-preorigin-travel-development.json"
PROPOSALS = BASE / "pwg2022-preorigin-travel-rescue-proposals-development.json"
REVIEW = BASE / "pwg2022-full-match-event-review-segments-v3-preorigin-travel-development.json"
OUTPUT = BASE / "pwg2022-event-evidence-handoff-v3-development.json"


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def index(rows, key):
    result = {row[key]: row for row in rows}
    if len(result) != len(rows):
        raise ValueError(f"Duplicate {key}")
    return result


def build():
    v2 = json.loads(V2.read_text())
    union = json.loads(UNION.read_text())
    proposal_file = json.loads(PROPOSALS.read_text())
    reviews = json.loads(REVIEW.read_text())
    proposals = index(proposal_file["proposals"], "proposal_id")
    old_games = index(v2["games"], "recording_code")
    review_games = index(reviews["games"], "official_game_code")
    reserved = json.loads((ROOT / "validation/unseen-end/reservation.json").read_text())
    games = []
    for game in union["games"]:
        code = game["official_game_code"]
        source = game["source_sha256"]
        old = old_games[code]
        review = review_games[code]
        if (source == reserved["source_sha256"] or
                source != old["source_sha256"] or source != review["source_sha256"]):
            raise ValueError("Source mismatch or reserved-source overlap")
        old_rows = index(old["rows"], "event_id")
        review_rows = index(review["segments"], "event_id")
        if set(review_rows) != {event["event_id"] for event in game["events"]}:
            raise ValueError("Review and v3 union event IDs differ")
        rows = []
        for event in game["events"]:
            event_id = event["event_id"]
            if event_id in old_rows:
                prior = old_rows[event_id]
                if (prior["candidate_class"] != event["candidate_class"] or
                        prior["source_shot_ids"] != event["source_shot_ids"] or
                        prior["counter_id"] != event["counter_id"] or
                        prior["delivery_window_s"] != event["delivery_window_s"] or
                        prior["review_window_s"] != review_rows[event_id][
                            "review_window_s"]):
                    raise ValueError("V3 altered an existing v2 evidence record")
                rows.append(prior)
                continue
            proposal = proposals[event_id]
            track = proposal["receiving_track"]
            segment = review_rows[event_id]
            if (event["candidate_class"] !=
                    "counter_linked_preorigin_travel_provisional" or
                    proposal["recording_code"] != code or
                    proposal["source_sha256"] != source or
                    event["source_shot_ids"] != [proposal["origin_shot_id"],
                                                 proposal["receiving_shot_id"]] or
                    event["observed_travel_window_s"] != track["interval_s"] or
                    event["counter_id"] != proposal["counter_id"] or
                    event["colour"] != proposal["counter_colour"] or
                    proposal["visible_release_cue_s"] is not None or
                    proposal["physical_stone_identity_verified"] or
                    segment["delivery_window_s"] != event["delivery_window_s"]):
                raise ValueError("New preorigin-travel evidence differs from proposal")
            rows.append({
                "event_id": event_id,
                "candidate_class": event["candidate_class"],
                "source_shot_ids": event["source_shot_ids"],
                "counter_id": event["counter_id"],
                "event_colour": event["colour"],
                "event_colour_status": event["colour_status"],
                "delivery_window_s": event["delivery_window_s"],
                "review_window_s": segment["review_window_s"],
                "release_cue": {"status": "no_visible_release_cue",
                                "route": "preorigin_receiving_travel_counter",
                                "origin_shot_id": proposal["origin_shot_id"],
                                "time_s": None, "colour": None},
                "receiving_view": {"status": "cap_travel_counter_concordant_identity_unverified",
                                   "colour": track["colour"],
                                   "motion_interval_s": track["interval_s"],
                                   "physical_stone_identity_verified": False},
                "partial_board_links": [],
                "physical_release_time_s": None,
                "physical_settle_time_s": None,
                "persistent_stone_id": None,
                "continuous_trajectory": None,
                "settled_board_transition_verified": False,
                "simulation_ready": False,
            })
        if len(rows) != game["provisional_event_count"]:
            raise ValueError("V3 handoff event count changed")
        games.append({"recording_code": code, "source_sha256": source,
                      "event_count": len(rows),
                      "unique_release_cue_count": sum(
                          row["release_cue"]["time_s"] is not None for row in rows),
                      "two_view_source_colour_agreement_count": sum(
                          row["receiving_view"]["status"] ==
                          "source_colour_concordant_identity_unverified" for row in rows),
                      "partial_board_link_count": sum(len(row["partial_board_links"])
                                                      for row in rows),
                      "release_cue_and_partial_board_count": sum(
                          row["release_cue"]["time_s"] is not None and
                          bool(row["partial_board_links"]) for row in rows),
                      "preorigin_travel_without_release_count": sum(
                          row["candidate_class"] ==
                          "counter_linked_preorigin_travel_provisional" and
                          row["release_cue"]["time_s"] is None for row in rows),
                      "rows": rows})
    return {"status": "development_v3_event_evidence_handoff_not_simulation_ready",
            "input_sha256": {"v2_handoff": digest(V2), "v3_union": digest(UNION),
                             "preorigin_travel_proposal": digest(PROPOSALS),
                             "v3_review": digest(REVIEW),
                             "runner": digest(Path(__file__))},
            "event_count": sum(game["event_count"] for game in games),
            "unique_release_cue_count": sum(game["unique_release_cue_count"]
                                             for game in games),
            "two_view_source_colour_agreement_count": sum(
                game["two_view_source_colour_agreement_count"] for game in games),
            "partial_board_link_count": sum(game["partial_board_link_count"]
                                            for game in games),
            "release_cue_and_partial_board_count": sum(
                game["release_cue_and_partial_board_count"] for game in games),
            "preorigin_travel_without_release_count": sum(
                game["preorigin_travel_without_release_count"] for game in games),
            "games": games,
            "limitations": [
                "The B02 receiving track is travel evidence and cannot be used as a visible or exact release timestamp.",
                "No cross-view persistent stone identity or physical settled-board transition is verified.",
                "All game-state observations are partial and none of the 359 candidates is simulation-ready.",
                "The candidate union has no independent complete-match physical throw precision, recall or F1.",
            ]}


def main():
    payload = json.dumps(build(), indent=2) + "\n"
    if OUTPUT.exists() and OUTPUT.read_text() != payload:
        raise SystemExit("Existing v3 handoff differs from hashed inputs")
    if not OUTPUT.exists():
        OUTPUT.write_text(payload)
    print(f"Verified {OUTPUT}")


if __name__ == "__main__":
    main()
