"""Attach source-reviewed right-view motion to conserved full-match candidates.

Time/colour association is not physical cross-camera identity. Only moving
image prefixes are copied; parked tracker tails never become throw duration.
"""

from collections import Counter
from hashlib import sha256
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "validation/throw-event-benchmark/layout-router/full-2024-coverage/latvia24-full-v1"
HANDOFF = BASE / "full-match-candidate-partial-state-handoff.json"
YELLOW = BASE / "early-highres-body-handle-transfer-development.json"
YELLOW_REVIEW = BASE / "early-highres-body-upward-source-review.json"
RED = BASE / "early-highres-red-full-transfer-development.json"
RED_MOTION = BASE / "early-highres-red-motion-windows-development.json"
RED_REVIEW = BASE / "early-highres-red-upward-source-review.json"
LATE_RED = BASE / "end6-highres-red-full-transfer-development.json"
LATE_YELLOW = BASE / "end6-highres-body-handle-screen-development.json"
LOW_VIDEO = ROOT / "validation/throw-event-benchmark/canada-latvia-2024/source-360p.mp4"
EARLY_VIDEO = (
    ROOT / "validation/throw-event-benchmark/canada-latvia-2024/source-1080p-1650-2760.mp4"
)
LATE_VIDEO = ROOT / "validation/throw-event-benchmark/canada-latvia-2024/source-1080p-5670-6670.mp4"
OUT = BASE / "full-match-candidate-receiving-image-handoff-development.json"


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    if OUT.exists():
        raise SystemExit("Output exists; preserve first receiving-motion handoff")
    handoff = json.loads(HANDOFF.read_text())
    yellow = json.loads(YELLOW.read_text())
    yellow_review = json.loads(YELLOW_REVIEW.read_text())
    red = json.loads(RED.read_text())
    red_motion = json.loads(RED_MOTION.read_text())
    red_review = json.loads(RED_REVIEW.read_text())
    late_red = json.loads(LATE_RED.read_text())
    late_yellow = json.loads(LATE_YELLOW.read_text())
    if handoff["source_sha256"] != digest(LOW_VIDEO):
        raise ValueError("Full-match handoff source changed")
    if yellow["source_video_sha256"] != digest(EARLY_VIDEO) or red["source_video_sha256"] != digest(
        EARLY_VIDEO
    ):
        raise ValueError("Early high-resolution source changed")
    if late_red["source_video_sha256"] != digest(LATE_VIDEO) or late_yellow[
        "blind_video_sha256"
    ] != digest(LATE_VIDEO):
        raise ValueError("Late high-resolution source changed")
    if (
        red_motion["transfer_sha256"] != digest(RED)
        or red_review["video_sha256"] != digest(EARLY_VIDEO)
        or yellow_review["video_sha256"] != digest(EARLY_VIDEO)
    ):
        raise ValueError("Motion/review provenance differs from early transfer")
    if yellow_review["transfer_sha256"] != digest(YELLOW):
        raise ValueError("Yellow source review differs from transfer")
    early_hash = digest(EARLY_VIDEO)
    yellow_paths = {
        p["diagnostic_path_id"]: p
        for p in yellow["supported_image_paths"]
        if p["direction"] == "upward"
    }
    red_paths = {
        p["diagnostic_path_id"]: p
        for p in red["supported_image_paths"]
        if p["direction"] == "upward"
    }
    red_windows = {p["diagnostic_path_id"]: p for p in red_motion["paths"]}
    yellow_reviewed = {p["path_id"] for p in yellow_review["paths"]}
    red_reviewed = {p["candidate_id"] for p in red_review["paths"]}
    if set(yellow_paths) != yellow_reviewed or set(red_paths) != set(red_windows):
        raise ValueError("Source review or motion interpretation lacks a path")
    by_candidate = {}
    for source, rows in (
        ("yellow", yellow["candidate_context"]),
        ("red", red["candidate_context"]),
    ):
        for item in rows:
            key = item["candidate_id"]
            path_ids = (
                item["upward_body_handle_paths_started_within_25s"]
                if source == "yellow"
                else item["upward_path_ids_started_within_25s"]
            )
            if len(path_ids) > 1 or key in by_candidate:
                raise ValueError("Ambiguous or duplicate candidate association")
            if path_ids:
                by_candidate[key] = (source, path_ids[0])
    ordered = []
    for row in handoff["ordered_candidates"]:
        out = dict(row)
        association = by_candidate.get(row["candidate_id"])
        observation = None
        if association:
            colour, path_id = association
            if (
                row["colour_claim"] != colour
                or row["observation_kind"] != "left_provisional_passage"
            ):
                raise ValueError("Right path attached to incompatible left row")
            if colour == "red":
                path = red_paths[path_id]
                motion = red_windows[path_id]
                last = motion["observed_moving_prefix_last_s"]
                if (
                    row["candidate_id"] not in red_reviewed
                    or red_review["same_agent_source_review"][row["candidate_id"].split("-")[-1]][
                        "moving_prefix"
                    ]
                    != "source_visible_moving_red_stone"
                ):
                    raise ValueError("Red path lacks source review")
                visual_stop = motion["visual_stop_bracket_s"]
                first = motion["observed_moving_prefix_first_s"]
            else:
                path = yellow_paths[path_id]
                if yellow_review["same_agent_source_review"][path_id] not in (
                    "source_visible_moving_yellow_stone",
                    "source_visible_moving_yellow_stone_template_source_event",
                ):
                    raise ValueError("Yellow path lacks source review")
                first, last = path["first_observed_s"], path["last_observed_s"]
                visual_stop = None
            points = [p for p in path["points"] if first <= p["time_s"] <= last]
            observation = {
                "status": "source_visible_moving_stone_temporally_associated_not_physical_identity",
                "colour_claim": colour,
                "diagnostic_path_id": path_id,
                "early_video_sha256": early_hash,
                "visible_moving_interval_s": [first, last],
                "image_center_points_1080p": [
                    {
                        "time_s": p["time_s"],
                        "center_px": p["center_1080p_px"],
                        "body_match_score": p["score"],
                    }
                    for p in points
                ],
                "visual_stop_bracket_s": visual_stop,
                "visual_stop_is_physical_stop": False,
                "same_physical_stone_as_left_verified": False,
                "persistent_stone_identity_verified": False,
                "metric_trajectory": None,
                "simulation_ready": False,
            }
        out["receiving_image_motion"] = observation
        if {k: v for k, v in out.items() if k != "receiving_image_motion"} != row:
            raise ValueError("Original candidate content changed")
        ordered.append(out)
    if len(ordered) != handoff["candidate_count"]:
        raise ValueError("Original candidate count changed")
    counts = Counter(
        r["receiving_image_motion"]["colour_claim"] for r in ordered if r["receiving_image_motion"]
    )
    result = {
        "status": "full_match_candidate_evidence_with_receiving_image_motion_not_physical_game_states",
        "source_id": handoff["source_id"],
        "source_sha256": handoff["source_sha256"],
        "source_interval_s": handoff["source_interval_s"],
        "base_handoff_sha256": digest(HANDOFF),
        "yellow_transfer_sha256": digest(YELLOW),
        "yellow_source_review_sha256": digest(YELLOW_REVIEW),
        "red_transfer_sha256": digest(RED),
        "red_motion_window_sha256": digest(RED_MOTION),
        "red_source_review_sha256": digest(RED_REVIEW),
        "late_red_transfer_sha256": digest(LATE_RED),
        "late_yellow_screen_sha256": digest(LATE_YELLOW),
        "runner_sha256": digest(Path(__file__)),
        "candidate_count": len(ordered),
        "receiving_image_motion_count_by_colour": dict(counts),
        "visual_stop_candidate_count": sum(
            r["receiving_image_motion"] is not None
            and r["receiving_image_motion"]["visual_stop_bracket_s"] is not None
            for r in ordered
        ),
        "left_trigger_blind_intervals": handoff["left_trigger_blind_intervals"],
        "late_right_image_probe": {
            "interval_s": late_red["source_interval_s"],
            "red_upward_path_count": late_red["red_supported_path_direction_counts"].get(
                "upward", 0
            ),
            "yellow_upward_path_count": late_yellow["supported_path_direction_counts"].get(
                "upward", 0
            ),
            "interval_throw_free_verified": False,
        },
        "ordered_candidates": ordered,
        "complete_throw_sequence_verified": False,
        "limitations": [
            "Temporal left/right association and source-visible motion do not prove same physical stone.",
            "The right-view points are image coordinates, not calibrated rink positions.",
            "A visual stillness bracket does not verify a physical stop or complete board.",
            "No independent exhaustive throw labels or event F1 are available.",
        ],
    }
    OUT.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(
        json.dumps(
            {
                "candidates": len(ordered),
                "receiving": dict(counts),
                "visual_stop_candidates": result["visual_stop_candidate_count"],
            }
        )
    )


if __name__ == "__main__":
    main()
