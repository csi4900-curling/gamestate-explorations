"""Cross-check Latvia reviewed onset brackets against high-res body paths."""

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
MOVING = BASE / "end6-split-panel-registration-czech-rule-transfer-development.json"
QUIET = BASE / "end6-split-panel-registration-held-path-controls-development.json"
OUTPUT = BASE / "end6-highres-body-onset-crosscheck-development.json"


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def classify(bracket, reference):
    if bracket is None:
        return "insufficient_highres_prelude"
    if bracket == reference:
        return "exact_cross_resolution_bracket_agreement"
    if max(abs(a - b) for a, b in zip(bracket, reference)) <= 1:
        return "within_one_second_cross_resolution_bracket_agreement"
    return "onset_bracket_disagreement"


def main():
    if OUTPUT.exists():
        raise ValueError("High-resolution onset cross-check already exists")
    join, yellow, red, moving, quiet = (
        json.loads(p.read_text()) for p in (JOIN, YELLOW, RED, MOVING, QUIET)
    )
    source_hash = join["highres_source_sha256"]
    if (
        source_hash != yellow["blind_video_sha256"]
        or source_hash != red["source_video_sha256"]
        or source_hash != moving["source_video_sha256"]
        or source_hash != quiet["source_video_sha256"]
        or moving["join_sha256"] != digest(JOIN)
        or quiet["join_sha256"] != digest(JOIN)
    ):
        raise ValueError("Path, source or registration lineage differs")
    paths = {("yellow", p["diagnostic_path_id"]): p for p in yellow["supported_image_paths"]}
    paths.update({("red", p["diagnostic_path_id"]): p for p in red["red_supported_image_paths"]})
    rows = []
    for item in join["rows"]:
        if item["source_prefix_class"] != "moving_stone_pixels":
            continue
        compatible = item["compatible_highres_paths"]
        if len(compatible) != 1:
            raise ValueError("Reviewed stone lacks unique high-res path")
        key = (item["colour_claim"], compatible[0]["highres_path_id"])
        points = paths[key]["points"]
        # Full-source 1080p -> 640x720 analysis scale: 2/3. The 360p
        # source used by the reference onset rule is another factor of 2
        # smaller, so its 3/12 px/s thresholds become 6/24 px/s here.
        normalized = [
            {"time_s": p["time_s"], "pixel": [value * 2 / 3 for value in p["center_1080p_px"]]}
            for p in points
        ]
        onset = observed_quiet_to_motion(
            normalized,
            "positive_y",
            quiet_rate_px_s=6,
            strong_rate_px_s=24,
            quiet_steps=3,
            strong_steps=2,
        )
        bracket = onset.get("onset_bracket_s")
        reference = item["observed_motion_onset"]["onset_bracket_s"]
        rows.append(
            {
                "right_proposal_id": item["right_proposal_id"],
                "colour": key[0],
                "highres_path_id": key[1],
                "highres_path_interval_s": [points[0]["time_s"], points[-1]["time_s"]],
                "highres_point_count": len(points),
                "reference_360p_bracket_s": reference,
                "highres_onset_status": onset["status"],
                "highres_bracket_s": bracket,
                "comparison": classify(bracket, reference),
                "physical_release_time_s": None,
                "physical_stone_identity_verified": False,
            }
        )
    counts = Counter(r["comparison"] for r in rows)
    payload = {
        "status": "same_match_cross_resolution_onset_check_not_event_accuracy",
        "source_video_sha256": source_hash,
        "join_sha256": digest(JOIN),
        "yellow_path_sha256": digest(YELLOW),
        "red_path_sha256": digest(RED),
        "moving_registration_sha256": digest(MOVING),
        "quiet_registration_sha256": digest(QUIET),
        "onset_code_sha256": digest(ROOT / "prototype/right_motion_onset.py"),
        "runner_sha256": digest(Path(__file__)),
        "method": "Existing quiet-to-directed-motion rule applied to full 1080p body paths at 640x720 analysis scale; 360p 3/12 px/s thresholds geometrically scaled to 6/24 px/s; compare with existing source-reviewed 360p onset brackets.",
        "reviewed_moving_stone_pixel_path_count": len(rows),
        "comparison_counts": dict(counts),
        "rows": rows,
        "limitations": [
            "The 360p reference brackets and high-resolution paths are same-match development evidence, not independent physical release labels.",
            "The underlying 360p and 1080p tracks may share source and detector biases; bracket agreement is not throw precision or recall.",
            "This check uses body-path source pixels; prior panel registration found small camera correction on these selected intervals, but the onset rule does not yet consume camera-relative residuals.",
        ],
    }
    OUTPUT.write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps({"paths": len(rows), "comparisons": dict(counts)}))


if __name__ == "__main__":
    main()
