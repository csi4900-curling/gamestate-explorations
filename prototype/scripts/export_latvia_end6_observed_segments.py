"""Join 1080p appearance, onset and motion into explicit observed segments."""

from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from right_motion_onset import observed_quiet_to_motion  # noqa: E402

BASE = ROOT / "validation/throw-event-benchmark/canada-latvia-2024"
LANE = ROOT / "validation/throw-event-benchmark/layout-router/full-2024-coverage/latvia24-full-v1"
JOIN = BASE / "end6-cross-resolution-body-cap-development.json"
YELLOW = LANE / "end6-highres-body-handle-screen-development.json"
RED = LANE / "end6-highres-red-full-transfer-development.json"
CONTEXT = BASE / "end6-highres-underpoint-context-development.json"
ONSET = BASE / "end6-highres-body-onset-crosscheck-development.json"
MOTION = BASE / "end6-split-panel-registration-czech-rule-transfer-development.json"
OUT = BASE / "end6-highres-observed-segments-development.json"


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def segment_tier(onset, context):
    if onset["status"] == "observed_quiet_to_sustained_directional_motion":
        if context == "clear_context_review":
            return "observed_onset_clear_appearance_candidate"
        return "observed_onset_appearance_requires_review"
    if context == "clear_context_review":
        return "clear_appearance_onset_unobserved_review"
    return "onset_unobserved_appearance_requires_review"


def main():
    if OUT.exists():
        raise ValueError("Observed segment ledger already exists")
    join, yellow, red, context, onset, motion = (
        json.loads(p.read_text()) for p in
        (JOIN, YELLOW, RED, CONTEXT, ONSET, MOTION))
    source_hash = join["highres_source_sha256"]
    if (len({source_hash, yellow["blind_video_sha256"],
             red["source_video_sha256"], context["source_video_sha256"],
             onset["source_video_sha256"], motion["source_video_sha256"]})
            != 1 or context["join_sha256"] != digest(JOIN) or
            onset["join_sha256"] != digest(JOIN) or
            motion["join_sha256"] != digest(JOIN)):
        raise ValueError("Input source or join lineage differs")
    source_paths = {("yellow", p["diagnostic_path_id"]): p
                    for p in yellow["supported_image_paths"]}
    source_paths.update({("red", p["diagnostic_path_id"]): p
                         for p in red["red_supported_image_paths"]})
    matched = {}
    for row in join["rows"]:
        if row["source_prefix_class"] != "moving_stone_pixels":
            continue
        compatible = row["compatible_highres_paths"]
        if len(compatible) != 1:
            raise ValueError("Reviewed moving prefix lacks unique body path")
        key = (row["colour_claim"], compatible[0]["highres_path_id"])
        if key in matched:
            raise ValueError("Duplicate high-resolution body association")
        matched[key] = row
    context_by_id = {r["path_id"]: r for r in context["rows"]}
    onset_by_id = {r["right_proposal_id"]: r for r in onset["rows"]}
    motion_by_id = {r["right_proposal_id"]: r for r in motion["rows"]}
    if (len(context_by_id) != 19 or len(onset_by_id) != 16 or
            len(matched) != 16):
        raise ValueError("Expected reviewed end-six source inventory differs")
    rows = []
    for (colour, path_id), path in sorted(source_paths.items()):
        association = matched.get((colour, path_id))
        key = association["right_proposal_id"] if association else path_id
        appearance = context_by_id[key]
        if association:
            stored = onset_by_id[key]
            onset_status = stored["highres_onset_status"]
            bracket = stored["highres_bracket_s"]
            camera = motion_by_id[key]
            camera_evidence = {
                "status": "reviewed_moving_prefix_pairs_audited",
                "pair_count": camera["pair_count"],
                "registered_pair_count": camera["registered_pair_count"],
                "residuals_px": [p["camera_residual_px"]
                                 for p in camera["pairs"]],
            }
            board_status = association["following_partial_image_state_status"]
        else:
            points = [{"time_s": p["time_s"],
                       "pixel": [value * 2 / 3
                                 for value in p["center_1080p_px"]]}
                      for p in path["points"]]
            measured = observed_quiet_to_motion(
                points, "positive_y", quiet_rate_px_s=6,
                strong_rate_px_s=24)
            onset_status = measured["status"]
            bracket = measured.get("onset_bracket_s")
            camera_evidence = {
                "status": "not_audited_unmatched_short_path",
                "pair_count": None, "registered_pair_count": None,
                "residuals_px": None,
            }
            board_status = "not_associated_to_reviewed_stone_prefix"
        if appearance["review_tier"] == "context_unavailable":
            raise ValueError("Selected path lacks appearance observation")
        onset_record = {"status": onset_status,
                        "bracket_s": bracket,
                        "time_semantics": "observed_image_motion_transition_not_physical_release"}
        rows.append({
            "segment_id": f"{colour}:{path_id}",
            "colour_claim": colour,
            "source_interval_s": [path["first_observed_s"],
                                  path["last_observed_s"]],
            "coordinate_frame": "source_1920x1080_full_image_right_panel_pixels",
            "observed_image_points": [{"source_time_s": p["time_s"],
                                       "body_center_1080p_px": p[
                                           "center_1080p_px"],
                                       "body_template_score": p["score"],
                                       "handle_colour_pixels": p[
                                           "handle_colour_pixels"]}
                                      for p in path["points"]],
            "appearance": {
                "review_tier": appearance["review_tier"],
                "median_underpoint_nonice_fraction": appearance[
                    "median_underpoint_nonice_fraction"],
                "sample_count": appearance["available_sample_count"],
            },
            "onset": onset_record,
            "camera_relative_motion": camera_evidence,
            "candidate_tier": segment_tier(onset_record,
                                           appearance["review_tier"]),
            "source_review_class_for_audit_only": appearance[
                "source_pixel_class"],
            "source_review_class_used_directly_for_tier": False,
            "source_review_influenced_path_and_sample_selection": True,
            "associated_right_proposal_id": (
                association["right_proposal_id"] if association else None),
            "following_partial_image_state_status": board_status,
            "physical_release_time_s": None,
            "physical_settle_time_s": None,
            "physical_stone_identity_verified": False,
            "inter_camera_identity_verified": False,
            "complete_game_state": False,
            "metric_trajectory_verified": False,
            "simulation_ready": False,
        })
    if len(rows) != 19 or len({r["segment_id"] for r in rows}) != 19:
        raise ValueError("Full high-resolution path inventory differs")
    tiers = Counter(r["candidate_tier"] for r in rows)
    payload = {
        "status": "observed_image_segment_evidence_not_physical_throw_sequence",
        "source_video_sha256": source_hash,
        "input_sha256": {"join": digest(JOIN), "yellow_paths": digest(YELLOW),
                         "red_paths": digest(RED), "appearance": digest(CONTEXT),
                         "onset": digest(ONSET), "camera_motion": digest(MOTION)},
        "runner_sha256": digest(Path(__file__)),
        "onset_code_sha256": digest(ROOT / "prototype/right_motion_onset.py"),
        "segment_count": len(rows),
        "candidate_tier_counts": dict(tiers),
        "source_review_class_used_directly_for_tier": False,
        "source_review_influenced_path_and_sample_selection": True,
        "rows": rows,
        "limitations": [
            "The interval is previously exposed development material, not an independent full-match throw benchmark.",
            "Observed image paths can change physical identity; onset and endpoint are not physical release or settle times.",
            "The appearance ambiguity boundary was chosen after source inspection; candidate tiers are review priorities, not validated throw decisions.",
            "Source review selected the 16 matched moving prefixes and their appearance sample times, even though the class string is not used directly by the tier rule.",
            "Partial board status is not a same-stone transition or complete game state.",
        ],
    }
    OUT.write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps({"segments": len(rows), "tiers": dict(tiers)}))


if __name__ == "__main__":
    main()
