"""First source-only Swiss transfer of the frozen China wide-contact route."""

from hashlib import sha256
import json
from math import dist
from pathlib import Path
import sys
from statistics import median

import cv2
import numpy as np
from scipy.optimize import linear_sum_assignment

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from prototype.image_space_stone_cluster import stable_image_caps
from prototype.scripts.audit_china_end2_wide_view_caps import wide_house_ellipse
from prototype.stone_motion_fallback import stone_cap_candidates
from prototype.cap_patch_verifier import score_candidates
from prototype.stone_patch_detector import load_model
from prototype.wide_view_ground_contact import contact_below_cap

BASE = ROOT / "validation/official-shot-sequence"
VIDEO = ROOT / "validation/throw-event-benchmark/paralympics-2022-sweden-switzerland/source.mp4"
MODEL = ROOT / "validation/curlobserver-learned-probe/cap-patch-crossmatch-v1/model-excluding-swiss-transfer.npz"
PRIOR = BASE / "swiss-end2-adjacent-video-boards-first.json"
CHINA_CONTACT = BASE / "china-end2-wide-body-contact-diagnostic.json"
OUTPUT = BASE / "swiss-end2-wide-contact-first-transfer.json"


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def compare_source_boards(wide, overhead, *, tolerance=0.25):
    """One-to-one same-colour source overlap; neither view is an official label."""
    matches = []
    for colour in ("red", "yellow"):
        left = [row for row in wide if row["colour"] == colour]
        right = [row for row in overhead if row["colour"] == colour]
        if not left or not right:
            continue
        cost = np.asarray([[dist(
            (a["canonical_lateral_house_radii"], a["longitudinal_house_radii"]),
            (b["canonical_lateral_house_radii"], b["longitudinal_house_radii"]))
            for b in right] for a in left])
        for li, ri in zip(*linear_sum_assignment(cost)):
            if cost[li, ri] <= tolerance:
                matches.append({"colour": colour,
                                "wide_index_within_colour": int(li),
                                "overhead_index_within_colour": int(ri),
                                "distance_house_radii": round(float(cost[li, ri]), 4)})
    return {"matched_count": len(matches), "matches": matches}


def main():
    if OUTPUT.exists():
        raise SystemExit("Output exists; preserve first Swiss wide transfer")
    prior = json.loads(PRIOR.read_text())
    china = json.loads(CHINA_CONTACT.read_text())
    source_hash = digest(VIDEO)
    if source_hash != prior["source_sha256"] or source_hash == china["source_sha256"]:
        raise ValueError("Source fingerprint mismatch")
    reserved = json.loads((ROOT / "validation/unseen-end/reservation.json").read_text())
    if source_hash == reserved["source_sha256"]:
        raise ValueError("Reserved source selected")
    model = load_model(MODEL)
    capture = cv2.VideoCapture(str(VIDEO), cv2.CAP_FFMPEG,
                               [cv2.CAP_PROP_N_THREADS, 1])
    fps = capture.get(cv2.CAP_PROP_FPS)
    rows = []
    for shot in prior["rows"]:
        frames = []
        for offset_s in shot["sampled_offsets_s"]:
            time_s = shot["counter_anchor_s"] + offset_s
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
                raw = stone_cap_candidates(frame, colour,
                                           allow_bright_body=True,
                                           allow_large_caps=True)
                for candidate in score_candidates(frame, raw, model):
                    if candidate["patch_score"] < -0.6:
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
        if stable and shot["stable_partial_board"]:
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
                                         "source_overlap": compare_source_boards(
                                             points, shot["stable_partial_board"])})
        rows.append({"shot_id": shot["shot_id"],
                     "sampled_time_count": len(shot["sampled_offsets_s"]),
                     "wide_ellipse_frame_count": len(frames),
                     "wide_frames": frames,
                     "stable_contact_tracks": stable,
                     "overhead_partial_board": shot["stable_partial_board"],
                     "source_only_orientation_alternatives": alternatives})
    capture.release()
    output = {
        "status": "first_cross_recording_source_only_wide_body_contact_transfer",
        "source_sha256": source_hash,
        "prior_board_scan_sha256": digest(PRIOR),
        "china_contact_diagnostic_sha256": digest(CHINA_CONTACT),
        "model_sha256": digest(MODEL),
        "contact_code_sha256": digest(ROOT / "prototype/wide_view_ground_contact.py"),
        "runner_sha256": digest(Path(__file__)),
        "shot_ids": [row["shot_id"] for row in rows],
        "rows": rows,
        "limitations": [
            "The Swiss source and its earlier overhead boards were exposed development material.",
            "The wide-house and contact rules were frozen before this Swiss scan, but the source was not a reserved independent test.",
            "Only the prior source-only counter-window offsets were scanned; wide shots outside them are unmeasured.",
            "The one-stone wide overlap cannot establish orientation where same-colour board positions are near a 180-degree symmetry.",
            "No official diagram positions enter selection or source-only overlap.",
            "No wide board is exported as a simulation-ready state.",
        ],
    }
    OUTPUT.write_text(json.dumps(output, indent=2) + "\n")
    print([(row["shot_id"], row["wide_ellipse_frame_count"],
            len(row["stable_contact_tracks"]),
            [(alt["lateral_sign"], alt["longitudinal_sign"],
              alt["source_overlap"]["matched_count"])
             for alt in row["source_only_orientation_alternatives"]])
           for row in rows])


if __name__ == "__main__":
    main()
