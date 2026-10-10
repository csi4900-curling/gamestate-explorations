"""First other-recording transfer of the frozen blue-ring wide-body route."""

from hashlib import sha256
import json
from pathlib import Path
import sys
from statistics import median

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from prototype.cap_patch_verifier import score_candidates
from prototype.image_space_stone_cluster import stable_image_caps
from prototype.scripts.audit_china_end2_wide_view_caps import wide_house_ellipse
from prototype.scripts.audit_swiss_end2_wide_contact_transfer import compare_source_boards
from prototype.stone_patch_detector import load_model
from prototype.wide_view_cap_proposal import wide_view_cap_candidates
from prototype.wide_view_ground_contact import contact_below_cap

BASE = ROOT / "validation/official-shot-sequence"
VIDEO = ROOT / "validation/throw-event-benchmark/paralympics-2022-slovakia-usa/source.mp4"
MODEL = ROOT / "validation/curlobserver-learned-probe/cap-patch-crossmatch-v1/model-excluding-swiss-transfer.npz"
PRIOR = BASE / "pwg2022-temporal-partial-boards.json"
PLAN = BASE / "slovakia-wide-blue-ring-first-plan.json"
OUTPUT = BASE / "slovakia-wide-blue-ring-first-transfer.json"
GAME_CODE = "PREL000103"
MIN_PATCH_SCORE = -0.7


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    if OUTPUT.exists():
        raise SystemExit("Output exists; preserve first Slovakia wide transfer")
    plan = json.loads(PLAN.read_text())
    files = {"video": VIDEO, "model": MODEL, "prior": PRIOR,
             "proposal_code": ROOT / "prototype/wide_view_cap_proposal.py",
             "contact_code": ROOT / "prototype/wide_view_ground_contact.py",
             "runner": Path(__file__)}
    actual = {name: digest(path) for name, path in files.items()}
    if actual != plan["frozen_sha256"]:
        raise ValueError("Frozen input or code fingerprint mismatch")
    prior = json.loads(PRIOR.read_text())
    source_hash = actual["video"]
    if source_hash != prior["source_video_sha256_by_game"][GAME_CODE]:
        raise ValueError("Video source mismatch")
    reserved = json.loads((ROOT / "validation/unseen-end/reservation.json").read_text())
    if source_hash == reserved["source_sha256"]:
        raise ValueError("Reserved source selected")
    selected = [row for row in prior["rows"] if row["official_game_code"] == GAME_CODE]
    if ([row["official_shot_id"] for row in selected] != plan["shot_ids"]
            or [row["sampled_offsets_s"] for row in selected] != plan["offsets_s_by_shot"]):
        raise ValueError("Predeclared selection changed")
    model = load_model(MODEL)
    capture = cv2.VideoCapture(str(VIDEO), cv2.CAP_FFMPEG,
                               [cv2.CAP_PROP_N_THREADS, 1])
    fps = capture.get(cv2.CAP_PROP_FPS)
    rows = []
    for shot in selected:
        frames = []
        for offset in shot["sampled_offsets_s"]:
            time_s = shot["counter_time_s"] + offset
            capture.set(cv2.CAP_PROP_POS_FRAMES, round(time_s * fps))
            ok, frame = capture.read()
            if not ok:
                raise RuntimeError(f"Cannot decode {time_s} s")
            frame = cv2.resize(frame, (640, 360))
            ellipse = wide_house_ellipse(frame)
            if ellipse is None:
                continue
            candidates = []
            for colour in ("red", "yellow"):
                raw = wide_view_cap_candidates(frame, colour, ellipse)
                for candidate in score_candidates(frame, raw, model):
                    if candidate["patch_score"] < MIN_PATCH_SCORE:
                        continue
                    contact = contact_below_cap(frame, candidate["pixel"])
                    candidates.append({"colour": colour,
                                       "cap_pixel": candidate["pixel"],
                                       "patch_score": round(candidate["patch_score"], 3),
                                       "contact": contact})
            frames.append({"time_s": time_s, "ellipse": ellipse,
                           "candidates": candidates})
        accepted = [{"time_s": row["time_s"],
                     "candidates": [{"colour": item["colour"],
                                     "pixel": item["contact"]["pixel"],
                                     "patch_score": item["patch_score"]}
                                    for item in row["candidates"]
                                    if item["contact"] is not None]}
                    for row in frames]
        stable = stable_image_caps(accepted) if accepted else []
        alternatives = []
        overhead = shot["stable_partial_board"]
        if stable and overhead:
            ellipses = [row["ellipse"] for row in frames]
            cx = median(row["center_px"][0] for row in ellipses)
            cy = median(row["center_px"][1] for row in ellipses)
            rx = median(max(row["axis_lengths_px"]) / 2 for row in ellipses)
            ry = median(min(row["axis_lengths_px"]) / 2 for row in ellipses)
            for lateral_sign in (-1, 1):
                for longitudinal_sign in (-1, 1):
                    points = [{"colour": item["colour"],
                               "canonical_lateral_house_radii": round(
                                   lateral_sign * (item["pixel_center"][0] - cx) / rx, 4),
                               "longitudinal_house_radii": round(
                                   longitudinal_sign * (item["pixel_center"][1] - cy) / ry, 4)}
                              for item in stable]
                    alternatives.append({"lateral_sign": lateral_sign,
                                         "longitudinal_sign": longitudinal_sign,
                                         "wide_points": points,
                                         "source_overlap": compare_source_boards(points, overhead)})
        rows.append({"shot_id": shot["official_shot_id"],
                     "counter_anchor_s": shot["counter_time_s"],
                     "sampled_time_count": len(shot["sampled_offsets_s"]),
                     "wide_ellipse_frame_count": len(frames),
                     "wide_frames": frames,
                     "stable_contact_tracks": stable,
                     "overhead_partial_board": overhead,
                     "source_only_orientation_alternatives": alternatives})
    capture.release()
    output = {
        "status": "first_frozen_blue_ring_wide_contact_other_recording_transfer",
        "source_sha256": source_hash,
        "plan_sha256": digest(PLAN),
        "frozen_sha256": actual,
        "min_patch_score": MIN_PATCH_SCORE,
        "rows": rows,
        "limitations": [
            "The five shot anchors and offsets come from an earlier source-only board scan; this is not an exhaustive recording scan.",
            "The prior file also contains official postscore fields, which this runner never accesses.",
            "Wide ellipse detection, cap proposals, grey contact and temporal stability can each miss visible stones.",
            "Counter anchoring does not verify exact settled-board time or physical throw identity.",
            "No official diagram is consulted for selection, coordinate orientation or scoring.",
            "No wide board is exported as simulation-ready state.",
        ],
    }
    OUTPUT.write_text(json.dumps(output, indent=2) + "\n")
    print([(row["shot_id"], row["wide_ellipse_frame_count"],
            len(row["stable_contact_tracks"]),
            len(row["overhead_partial_board"])) for row in rows])


if __name__ == "__main__":
    main()
