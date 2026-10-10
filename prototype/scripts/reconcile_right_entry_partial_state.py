"""Conditionally link right-entry prefixes to earlier left events and partial boards."""

import argparse
from hashlib import sha256
import json
from pathlib import Path


def digest(path):
    h = sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--right", type=Path, required=True)
    parser.add_argument("--left-screen", type=Path, required=True)
    parser.add_argument("--partial-state", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists")
    right = json.loads(args.right.read_text())
    left = json.loads(args.left_screen.read_text())
    state = json.loads(args.partial_state.read_text())
    source_hashes = {right["source_sha256"], left["source_sha256"],
                     state["source_sha256"]}
    if len(source_hashes) != 1:
        parser.error("Source fingerprints differ")
    state_by_id = {row["candidate_id"]: row for row in state["events"]}
    if len(state_by_id) != len(state["events"]):
        parser.error("Duplicate partial-state candidate ID")
    rows = []
    for proposal in right["entry_review_proposals"]:
        t = proposal["entry_crossing"]["time_s"]
        candidates = [event for event in left["events"]
                      if event["colour"] == proposal["colour_claim"] and
                      0 <= t - event["crossing_time_s"] <= 20]
        candidates.sort(key=lambda event: t - event["crossing_time_s"])
        match = candidates[0] if len(candidates) == 1 else None
        board = state_by_id.get(match["id"]) if match else None
        if match and board is None:
            parser.error(f"Missing partial state for {match['id']}")
        rows.append({
            "right_raw_track_id": proposal["raw_track_id"],
            "right_colour_claim": proposal["colour_claim"],
            "right_entry_time_s": t,
            "same_colour_prior_left_ids_within_20s": [e["id"] for e in candidates],
            "match_status": "unique_conditional_time_colour_link" if match else
                            ("ambiguous_multiple_prior_left_events" if candidates else
                             "no_prior_left_event_within_20s"),
            "left_candidate_id": match["id"] if match else None,
            "left_crossing_time_s": match["crossing_time_s"] if match else None,
            "right_minus_left_lag_s": round(t - match["crossing_time_s"], 3)
                                      if match else None,
            "post_event_board_status": board["post_event_observation"]["status"]
                                       if board else None,
            "partial_state_simulation_ready": board["simulation_ready"] if board else None,
            "physical_cross_view_identity_verified": False,
        })
    result = {
        "status": "conditional_right_left_partial_state_links_not_identity_validation",
        "source_sha256": right["source_sha256"],
        "right_sha256": digest(args.right),
        "left_screen_sha256": digest(args.left_screen),
        "partial_state_sha256": digest(args.partial_state),
        "runner_sha256": digest(Path(__file__)),
        "match_rule": "Same colour, accepted left event preceding right entry by 0–20 s; exactly one required.",
        "right_entry_count": len(rows),
        "unique_conditional_link_count": sum(row["match_status"] ==
                                             "unique_conditional_time_colour_link" for row in rows),
        "links": rows,
        "limitations": [
            "Time and colour concordance do not verify the same physical stone across views.",
            "Both entry tiers and partial boards are exposed development evidence.",
            "A partial board is camera-local and neither complete nor metric-accuracy verified.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"entries": len(rows),
                      "unique_links": result["unique_conditional_link_count"]}))


if __name__ == "__main__":
    main()
