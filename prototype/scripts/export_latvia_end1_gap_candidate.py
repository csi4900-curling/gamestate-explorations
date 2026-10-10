"""Add source-reviewed area path A008 to Latvia's ordered candidate handoff."""

import argparse
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("handoff", "area-probe", "episodes", "context", "source-review",
                 "source-manifest", "output"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists")
    paths = {"handoff": args.handoff, "area_probe": args.area_probe,
             "episodes": args.episodes, "context": args.context,
             "source_review": args.source_review,
             "source_manifest": args.source_manifest}
    data = {key: json.loads(path.read_text()) for key, path in paths.items()}
    old, probe, episodes, context = (data[key] for key in
                                     ("handoff", "area_probe", "episodes", "context"))
    review, manifest = data["source_review"], data["source_manifest"]
    source_hash = old["source_sha256"]
    if any(item["source_sha256"] != source_hash for item in
           (probe, episodes, context, review, manifest)):
        parser.error("Input source hashes disagree")
    if (episodes["input_sha256"]["right"] != digest(args.area_probe) or
            context["input_sha256"]["probe"] != digest(args.area_probe) or
            context["input_sha256"]["episodes"] != digest(args.episodes) or
            review["probe_sha256"] != digest(args.area_probe) or
            review["manifest_sha256"] != digest(args.source_manifest) or
            manifest["probe_sha256"] != digest(args.area_probe)):
        parser.error("Area probe, episode, context and review lineage disagree")
    matches = [item for item in probe["directional_review_proposals"]
               if item["raw_track_id"] == "A008"]
    episode_rows = [item for item in episodes["episodes"]
                    if item["right_proposal_ids"] == ["R01:A008"]]
    contexts = [item for item in context["rows"]
                if item["right_proposal_id"] == "R01:A008"]
    if (len(matches) != 1 or len(episode_rows) != 1 or len(contexts) != 1 or
            len(review["review"]) != 1 or len(manifest["rows"]) != 1):
        parser.error("A008 must be unique in every source artifact")
    motion, episode, cue, source_class = matches[0], episode_rows[0], contexts[0], review["review"][0]
    time_s = motion["passage"]["time_s"]
    if (motion["colour_claim"] != "red" or motion["direction"] != "negative_y" or
            episode["episode_kind"] != "right_only_candidate" or
            episode["observation_time_s"] != time_s or
            source_class["right_proposal_id"] != "R01:A008" or
            source_class["sampled_prefix_class"] != "moving_stone_pixels" or
            source_class["passage_time_s"] != time_s or
            cue["review_tier"] != "clear_context_review" or
            manifest["rows"][0]["right_proposal_id"] != "R01:A008"):
        parser.error("A008 source evidence disagrees")
    if not 200 <= time_s <= 1050:
        parser.error("A008 is outside the stable first-end marker window")
    prior_rows = old["ordered_candidates"]
    if (old["candidate_count"] != 148 or old["development_possible_event_review_count"] != 97 or
            old["physical_throw_count_verified"] is not None or
            any(row["candidate_id"] == "right_area:R01:A008" or
                (row["colour_claim"] == "red" and
                 abs(row["source_time_s"] - time_s) <= 2)
                for row in prior_rows)):
        parser.error("Prior handoff is not the expected nonduplicated review ledger")
    state = deepcopy(prior_rows[0]["game_state_after"])
    if state["simulation_ready"]:
        parser.error("Prior state unexpectedly simulation-ready")
    candidate = {
        "candidate_id": "right_area:R01:A008",
        "source_time_s": time_s,
        "time_semantics": motion["passage_kind"],
        "colour_claim": "red",
        "observation_kind": "right_area_end1_reviewed_stone_pixels",
        "evidence_tier": "same_agent_short_stone_pixel_path_not_physical_throw",
        "left_screen_reason": "no_compatible_left_candidate_in_area_inventory",
        "left_coverage_status": "sampled_left_activity_supported",
        "observed_motion": {
            "camera": "right_360p",
            "coordinate_frame": "source_image_pixels_not_metric_ice",
            "direction": motion["direction"],
            "observed_prefix_interval_s": motion["observed_prefix_interval_s"],
            "observed_prefix_points": motion["observed_prefix_points"],
            "physical_stone_identity_verified": False,
        },
        "right_context_review_tier": cue["review_tier"],
        "post_candidate_partial_board": None,
        "terminal_visibility": None,
        "physical_throw_verified": False,
        "game_state_after": state,
        "source_pixel_review": {
            "source_pixel_class": source_class["sampled_prefix_class"],
            "review_origin": "same_agent_prediction_and_sequence_targeted",
            "image_path": "end1-gap-right-area-source-review/sheet-01.jpg",
            "physical_throw_verified": False,
        },
        "sequence_id": None,
    }
    rows = sorted([*prior_rows, candidate],
                  key=lambda row: (row["source_time_s"], row["candidate_id"]))
    for index, row in enumerate(rows, 1):
        row["merged_order_index"] = index
    output = deepcopy(old)
    output["status"] = "development_latvia_full_candidate_handoff_with_end1_end5_gap_reviews_not_throw_truth"
    output["ordered_candidates"] = rows
    output["candidate_count"] = len(rows)
    output["candidate_counts_by_kind"] = {**old["candidate_counts_by_kind"],
                                           candidate["observation_kind"]: 1}
    output["development_possible_event_review_count"] = old["development_possible_event_review_count"] + 1
    output["end1_gap_area_candidate_count"] = 1
    output["physical_throw_count_verified"] = None
    output["complete_throw_sequence_verified"] = False
    output["provenance"] = {**old["provenance"],
                            "end1_gap_inputs_sha256": {key: digest(path)
                                                        for key, path in paths.items()},
                            "end1_gap_runner_sha256": digest(Path(__file__))}
    output["limitations"] = [*old["limitations"],
        "A008 is a same-agent source-reviewed short red stone-pixel path, not an independently verified physical throw.",
        "The 98-row possible-event review tier includes known person and ambiguous paths; it is not a shot count or F1 score."]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"candidates": len(rows),
                      "possible_event_reviews": output["development_possible_event_review_count"],
                      "added": candidate["candidate_id"]}))


if __name__ == "__main__":
    main()
