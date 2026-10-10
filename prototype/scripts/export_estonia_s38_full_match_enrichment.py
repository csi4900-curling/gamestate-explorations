"""Attach high-resolution S02 observations to the 360p full-match S38 row."""

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "validation/throw-event-benchmark/canada-estonia-2024"
FULL_VIDEO = BASE / "source.mp4"
INPUTS = {
    "full_sequence": BASE
    / "right-large-cap-full-candidate-pre-post-image-state-handoff-refined-coverage.json",
    "highres_bridge": BASE / "yellow-s02-cross-view-observation-handoff-postreview-v2.json",
    "left_partial_caps": BASE / "yellow-s02-left-post-partial-image-caps-postreview.json",
    "cross_resolution_alignment": BASE / "yellow-s02-cross-resolution-alignment-postreview.json",
}
OUTPUT = BASE / "full-match-s38-highres-state-enrichment-postreview.json"


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    data = {key: json.loads(path.read_text()) for key, path in INPUTS.items()}
    full, bridge, caps, alignment = (data[key] for key in INPUTS)
    if full["source_sha256"] != digest(FULL_VIDEO) or (
        alignment["full_source_sha256"] != full["source_sha256"]
        or alignment["excerpt_sha256"] != bridge["source_video_sha256"]
        or caps["source_video_sha256"] != bridge["source_video_sha256"]
        or caps["handoff_sha256"] != digest(INPUTS["highres_bridge"])
    ):
        raise ValueError("Source or high-resolution lineage mismatch")
    if not alignment["zero_offset_best_at_all_checkpoints"] or len(alignment["checkpoints"]) != 2:
        raise ValueError("No source-frame alignment support at event and board times")
    rows = [row for row in full["rows"] if row["candidate_id"] == "left:R01-S38"]
    if len(rows) != 1:
        raise ValueError("Full-match S38 row missing or duplicated")
    prior = rows[0]
    next_time = min(
        row["observation_time_s"]
        for row in full["rows"]
        if row["observation_time_s"] > prior["observation_time_s"]
    )
    if (
        full["source_id"] != "PXGfMeiTKMA"
        or prior["left_event_id"] != "R01-S38"
        or prior["right_temporal_candidate_ids"] != ["R01:A079"]
        or prior["colour_claim"] != bridge["colour_claim"]
        or prior["observation_time_s"] != bridge["candidate_crossing_time_s"]
        or bridge["candidate_id"] != "S02"
        or caps["candidate_id"] != "S02"
        or not bridge["right_view"]["samples"]
        or not bridge["left_view"]["samples"]
        or max(caps["selected_times_s"]) >= next_time
    ):
        raise ValueError("S38/S02 chronology, colour or candidate mapping changed")
    if (
        prior["game_state_after"]["simulation_ready"]
        or prior["game_state_after"]["complete_board"] is not None
        or bridge["game_state_after"]["simulation_ready"]
        or caps["complete_board_verified"]
        or caps["physical_settle_verified"]
    ):
        raise ValueError("Unverified state was promoted upstream")

    enriched = deepcopy(prior)
    enriched["high_resolution_evidence"] = {
        "source_video_sha256": bridge["source_video_sha256"],
        "source_time_alignment": "zero_offset_best_at_1759.5_and_1779.5_s_only",
        "right_moving_path": bridge["right_view"],
        "cross_view_handoff": bridge["handoff"],
        "left_receiving_path": bridge["left_view"],
        "post_event_left_partial_image_board": {
            "status": caps["status"],
            "selected_times_s": caps["selected_times_s"],
            "repeated_caps": caps["repeated_caps"],
            "complete_board_verified": False,
            "delivered_stone_identity_verified": False,
            "physical_settle_verified": False,
            "camera_registration_verified": False,
            "simulation_ready": False,
        },
        "preexisting_right_post_candidate_status": prior["post_candidate_partial_cap_observation"][
            "status"
        ],
        "view_selection_note": "The post-event left panel shows the receiving house; the preexisting right post-candidate scan is not evidence that this left house lacks stones.",
    }
    output = {
        "status": "postreview_highres_single_candidate_full_match_enrichment_not_game_truth",
        "full_match_source_sha256": full["source_sha256"],
        "highres_excerpt_sha256": bridge["source_video_sha256"],
        "full_match_sequence_id": prior["sequence_id"],
        "next_full_match_candidate_time_s": next_time,
        "input_sha256": {key: digest(path) for key, path in INPUTS.items()},
        "runner_sha256": digest(Path(__file__)),
        "candidate_row": enriched,
        "complete_throw_sequence_verified": False,
        "simulation_ready": False,
        "limitations": [
            "The high-resolution excerpt and full source agree at two selected checkpoints, not globally.",
            "The full-match time/colour link and two-view identity were examined after the source was exposed.",
            "Repeated yellow image caps form a partial observation, not a complete physical board or delivered-stone ID.",
            "Only S38 is enriched; this does not solve full-match state reconstruction or event F1.",
        ],
    }
    OUTPUT.write_text(json.dumps(output, indent=2) + "\n")
    print(
        json.dumps(
            {
                "candidate": prior["candidate_id"],
                "partial_repeated_caps": len(caps["repeated_caps"]),
                "complete_board": enriched["game_state_after"]["complete_board"],
                "simulation_ready": output["simulation_ready"],
            }
        )
    )


if __name__ == "__main__":
    main()
