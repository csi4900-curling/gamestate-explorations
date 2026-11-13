"""Post-transfer Swiss wide-view cap proposal revision; source overlap only."""

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
VIDEO = ROOT / "validation/throw-event-benchmark/paralympics-2022-sweden-switzerland/source.mp4"
MODEL = (
    ROOT
    / "validation/curlobserver-learned-probe/cap-patch-crossmatch-v1/model-excluding-swiss-transfer.npz"
)
FIRST = BASE / "swiss-end2-wide-contact-first-transfer.json"
OUTPUT = BASE / "swiss-end2-wide-blue-ring-v2-development.json"
MIN_PATCH_SCORE = -0.7


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    if OUTPUT.exists():
        raise SystemExit("Output exists; preserve first v2 diagnostic")
    first = json.loads(FIRST.read_text())
    source_hash = digest(VIDEO)
    if source_hash != first["source_sha256"]:
        raise ValueError("Source fingerprint mismatch")
    reserved = json.loads((ROOT / "validation/unseen-end/reservation.json").read_text())
    if source_hash == reserved["source_sha256"]:
        raise ValueError("Reserved source selected")
    model = load_model(MODEL)
    capture = cv2.VideoCapture(str(VIDEO), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    fps = capture.get(cv2.CAP_PROP_FPS)
    rows = []
    for previous in first["rows"]:
        frames = []
        for old_frame in previous["wide_frames"]:
            time_s = old_frame["time_s"]
            capture.set(cv2.CAP_PROP_POS_FRAMES, round(time_s * fps))
            ok, frame = capture.read()
            if not ok:
                raise RuntimeError(f"Cannot decode {time_s} s")
            frame = cv2.resize(frame, (640, 360))
            ellipse = wide_house_ellipse(frame)
            if ellipse != old_frame["ellipse"]:
                raise ValueError("Wide ellipse changed from first transfer")
            candidates = []
            for colour in ("red", "yellow"):
                raw = wide_view_cap_candidates(frame, colour, ellipse)
                for candidate in score_candidates(frame, raw, model):
                    if candidate["patch_score"] < MIN_PATCH_SCORE:
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
        accepted = [
            {
                "time_s": row["time_s"],
                "candidates": [
                    {
                        "colour": item["colour"],
                        "pixel": item["contact"]["pixel"],
                        "patch_score": item["patch_score"],
                    }
                    for item in row["candidates"]
                    if item["contact"] is not None
                ],
            }
            for row in frames
        ]
        stable = stable_image_caps(accepted) if accepted else []
        alternatives = []
        if stable and previous["overhead_partial_board"]:
            ellipses = [row["ellipse"] for row in frames]
            cx = median(row["center_px"][0] for row in ellipses)
            cy = median(row["center_px"][1] for row in ellipses)
            rx = median(max(row["axis_lengths_px"]) / 2 for row in ellipses)
            ry = median(min(row["axis_lengths_px"]) / 2 for row in ellipses)
            for lateral_sign in (-1, 1):
                for longitudinal_sign in (-1, 1):
                    points = [
                        {
                            "colour": item["colour"],
                            "canonical_lateral_house_radii": round(
                                lateral_sign * (item["pixel_center"][0] - cx) / rx, 4
                            ),
                            "longitudinal_house_radii": round(
                                longitudinal_sign * (item["pixel_center"][1] - cy) / ry, 4
                            ),
                        }
                        for item in stable
                    ]
                    alternatives.append(
                        {
                            "lateral_sign": lateral_sign,
                            "longitudinal_sign": longitudinal_sign,
                            "wide_points": points,
                            "source_overlap": compare_source_boards(
                                points, previous["overhead_partial_board"]
                            ),
                        }
                    )
        rows.append(
            {
                "shot_id": previous["shot_id"],
                "wide_ellipse_frame_count": len(frames),
                "wide_frames": frames,
                "stable_contact_tracks": stable,
                "overhead_partial_board": previous["overhead_partial_board"],
                "source_only_orientation_alternatives": alternatives,
            }
        )
    capture.release()
    output = {
        "status": "post_first_transfer_blue_ring_proposal_development_not_frozen_score",
        "source_sha256": source_hash,
        "first_transfer_sha256": digest(FIRST),
        "model_sha256": digest(MODEL),
        "proposal_code_sha256": digest(ROOT / "prototype/wide_view_cap_proposal.py"),
        "contact_code_sha256": digest(ROOT / "prototype/wide_view_ground_contact.py"),
        "runner_sha256": digest(Path(__file__)),
        "min_patch_score": MIN_PATCH_SCORE,
        "rows": rows,
        "limitations": [
            "Blue-ring surroundings and -0.7 patch cutoff were chosen after inspecting the Swiss miss.",
            "The same source and five windows are development data, not independent validation.",
            "Two same-colour Swiss stones remain compatible with both 0- and 180-degree coordinate orientations.",
            "No official diagram is used, and no wide board is exported as game state.",
        ],
    }
    OUTPUT.write_text(json.dumps(output, indent=2) + "\n")
    print(
        [
            (
                row["shot_id"],
                len(row["stable_contact_tracks"]),
                [
                    (
                        alt["lateral_sign"],
                        alt["longitudinal_sign"],
                        alt["source_overlap"]["matched_count"],
                    )
                    for alt in row["source_only_orientation_alternatives"]
                ],
            )
            for row in rows
        ]
    )


if __name__ == "__main__":
    main()
