"""Postscore adjacent-shot check of frozen wide-body contact and view fusion."""

from hashlib import sha256
import json
from pathlib import Path
import sys
from statistics import median

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from prototype.board_state_comparison import compare_board_observations
from prototype.image_space_stone_cluster import stable_image_caps
from prototype.scripts.audit_china_end2_wide_view_caps import wide_house_ellipse
from prototype.stone_motion_fallback import stone_cap_candidates
from prototype.cap_patch_verifier import score_candidates
from prototype.stone_patch_detector import load_model
from prototype.wide_view_ground_contact import contact_below_cap

BASE = ROOT / "validation/official-shot-sequence"
VIDEO = ROOT / "validation/throw-event-benchmark/paralympics-2022-canada-china/source.mp4"
MODEL = (
    ROOT
    / "validation/curlobserver-learned-probe/cap-patch-crossmatch-v1/model-excluding-swiss-transfer.npz"
)
CLOSE = BASE / "china-end2-adjacent-video-boards-first.json"
PRIOR_CONTACT = BASE / "china-end2-wide-body-contact-diagnostic.json"
DIAGRAMS = BASE / "pwg2022-official-board-diagrams.json"
OUTPUT = BASE / "china-end2-s11-wide-fusion-development.json"
SHOT_ID = "PREL000102-E02-S11"
TIMES_S = (1603, 1603.5, 1604, 1604.5)


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    if OUTPUT.exists():
        raise SystemExit("Output exists; preserve first S11 wide-fusion diagnostic")
    close = json.loads(CLOSE.read_text())
    prior = json.loads(PRIOR_CONTACT.read_text())
    source_hash = digest(VIDEO)
    if source_hash != close["source_sha256"] or source_hash != prior["source_sha256"]:
        raise ValueError("Source fingerprint mismatch")
    reserved = json.loads((ROOT / "validation/unseen-end/reservation.json").read_text())
    if source_hash == reserved["source_sha256"]:
        raise ValueError("Reserved source selected")
    prior_orientation = next(
        row
        for row in prior["postscore_lateral_alternatives"]
        if row["orientation_status"] == "source_hypothesis_180_degree_view_reversal"
    )
    lateral_sign = prior_orientation["lateral_sign"]
    longitudinal_sign = prior["source_only_longitudinal_sign"]
    shot = next(row for row in close["rows"] if row["shot_id"] == SHOT_ID)
    if not (shot["counter_anchor_s"] < TIMES_S[0] and TIMES_S[-1] < shot["following_counter_s"]):
        raise ValueError("Wide samples outside S11 counter interval")
    model = load_model(MODEL)
    capture = cv2.VideoCapture(str(VIDEO), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    fps = capture.get(cv2.CAP_PROP_FPS)
    frames = []
    for time_s in TIMES_S:
        capture.set(cv2.CAP_PROP_POS_FRAMES, round(time_s * fps))
        ok, frame = capture.read()
        if not ok:
            raise RuntimeError(f"Cannot decode {time_s} s")
        frame = cv2.resize(frame, (640, 360))
        ellipse = wide_house_ellipse(frame)
        candidates = []
        for colour in ("red", "yellow"):
            raw = stone_cap_candidates(frame, colour, allow_bright_body=True, allow_large_caps=True)
            for candidate in score_candidates(frame, raw, model):
                if candidate["patch_score"] < -0.6:
                    continue
                contact = contact_below_cap(frame, candidate["pixel"])
                candidates.append(
                    {
                        "colour": colour,
                        "cap_pixel": candidate["pixel"],
                        "patch_score": round(candidate["patch_score"], 3),
                        "contact": contact,
                    }
                )
        frames.append({"time_s": time_s, "ellipse": ellipse, "candidates": candidates})
    capture.release()
    accepted = [
        {
            "time_s": frame["time_s"],
            "candidates": [
                {
                    "colour": row["colour"],
                    "pixel": row["contact"]["pixel"],
                    "patch_score": row["patch_score"],
                }
                for row in frame["candidates"]
                if row["contact"] is not None
            ],
        }
        for frame in frames
    ]
    stable = stable_image_caps(accepted, min_span_s=1.0)
    ellipses = [frame["ellipse"] for frame in frames]
    if any(ellipse is None for ellipse in ellipses):
        raise ValueError("Missing wide house ellipse")
    cx = median(ellipse["center_px"][0] for ellipse in ellipses)
    cy = median(ellipse["center_px"][1] for ellipse in ellipses)
    rx = median(max(ellipse["axis_lengths_px"]) / 2 for ellipse in ellipses)
    ry = median(min(ellipse["axis_lengths_px"]) / 2 for ellipse in ellipses)
    wide_points = [
        {
            "colour": row["colour"],
            "canonical_lateral_house_radii": round(
                lateral_sign * (row["pixel_center"][0] - cx) / rx, 4
            ),
            "longitudinal_house_radii": round(
                longitudinal_sign * (row["pixel_center"][1] - cy) / ry, 4
            ),
        }
        for row in stable
    ]
    # Retain the accepted S11 overhead centre observation as its own source.
    # The no-duplicate check prevents the two views from silently creating
    # duplicate physical stones at the same colour/board position.
    overhead = shot["stable_partial_board"]
    if any(
        v["colour"] == o["colour"]
        and (
            (v["canonical_lateral_house_radii"] - o["canonical_lateral_house_radii"]) ** 2
            + (v["longitudinal_house_radii"] - o["longitudinal_house_radii"]) ** 2
        )
        < 0.25**2
        for v in wide_points
        for o in overhead
    ):
        raise ValueError("Cross-view stone overlap needs identity resolution")
    fused = overhead + wide_points
    official = next(
        shot
        for game in json.loads(DIAGRAMS.read_text())["games"]
        for end in game["ends"]
        for shot in end["shots"]
        if shot["official_shot_id"] == SHOT_ID
    )
    score = compare_board_observations(
        fused, official["stones"], official_house_center_y=official["house_center_px"][1]
    )
    output = {
        "status": "selected_postscore_adjacent_wide_contact_and_overhead_fusion_not_exported",
        "shot_id": SHOT_ID,
        "source_sha256": source_hash,
        "model_sha256": digest(MODEL),
        "contact_code_sha256": digest(ROOT / "prototype/wide_view_ground_contact.py"),
        "prior_contact_sha256": digest(PRIOR_CONTACT),
        "close_video_board_sha256": digest(CLOSE),
        "official_diagrams_sha256": digest(DIAGRAMS),
        "runner_sha256": digest(Path(__file__)),
        "selected_times_s": list(TIMES_S),
        "counter_interval_s": [shot["counter_anchor_s"], shot["following_counter_s"]],
        "source_orientation_hypothesis": {
            "lateral_sign": lateral_sign,
            "longitudinal_sign": longitudinal_sign,
        },
        "frames": frames,
        "stable_wide_contacts": stable,
        "wide_contact_board_points": wide_points,
        "overhead_partial_board": overhead,
        "source_only_fused_points": fused,
        "postscore_comparison": score,
        "limitations": [
            "S11 wide times were selected after inspecting the earlier S12 diagnostic and S11 frames.",
            "The camera orientation is inherited from the selected S12 development hypothesis.",
            "The counter interval does not prove the next delivery had not begun or no impact occurred.",
            "The grey-body lower edge is an approximate ice contact, not metric calibration.",
            "Fusion does not establish persistent physical stone identities or a verified state transition.",
            "The official diagram is used only for postscore comparison.",
            "No result is promoted into the video-derived game-state export.",
        ],
    }
    OUTPUT.write_text(json.dumps(output, indent=2) + "\n")
    print(
        {
            "stable_wide_contacts": len(stable),
            "fused_points": len(fused),
            "postscore_matches": score["matched_count"],
            "mean_error": score["mean_matched_distance_house_radii"],
        }
    )


if __name__ == "__main__":
    main()
