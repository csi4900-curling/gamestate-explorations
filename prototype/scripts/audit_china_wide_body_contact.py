"""Source-only wide-view contact estimate, followed by a separate postscore audit."""

from hashlib import sha256
import json
from pathlib import Path
import sys
from statistics import median

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from prototype.board_state_comparison import compare_board_observations
from prototype.wide_view_ground_contact import contact_below_cap

BASE = ROOT / "validation/official-shot-sequence"
WIDE = BASE / "china-end2-wide-perspective-cap-evidence-development.json"
CLOSE = BASE / "china-end2-adjacent-video-boards-first.json"
DIAGRAMS = BASE / "pwg2022-official-board-diagrams.json"
VIDEO = ROOT / "validation/throw-event-benchmark/paralympics-2022-canada-china/source.mp4"
OUTPUT = BASE / "china-end2-wide-body-contact-diagnostic.json"
SHOT_ID = "PREL000102-E02-S12"


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    if OUTPUT.exists():
        raise SystemExit("Output exists; preserve first body-contact diagnostic")
    wide, close = (json.loads(path.read_text()) for path in (WIDE, CLOSE))
    if digest(VIDEO) != wide["source_sha256"] or close["source_sha256"] != wide["source_sha256"]:
        raise ValueError("Source fingerprint mismatch")
    reserved = json.loads((ROOT / "validation/unseen-end/reservation.json").read_text())
    if reserved["source_sha256"] == wide["source_sha256"]:
        raise ValueError("Reserved source selected")
    close_board = next(
        row["stable_partial_board"] for row in close["rows"] if row["shot_id"] == SHOT_ID
    )
    shared_yellow = next(row for row in close_board if row["colour"] == "yellow")
    capture = cv2.VideoCapture(str(VIDEO), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    fps = capture.get(cv2.CAP_PROP_FPS)
    frames = {}
    for row in wide["frames"]:
        capture.set(cv2.CAP_PROP_POS_FRAMES, round(row["time_s"] * fps))
        ok, frame = capture.read()
        if not ok:
            raise RuntimeError(f"Cannot decode {row['time_s']} s")
        frames[row["time_s"]] = cv2.resize(frame, (640, 360))
    capture.release()
    contacts = []
    for stone in wide["stable_image_caps"]:
        observations = []
        for row in wide["frames"]:
            candidates = [
                candidate
                for candidate in row["candidates"]
                if candidate["colour"] == stone["colour"]
            ]
            candidate = min(
                candidates,
                key=lambda item: (
                    (item["pixel"][0] - stone["pixel_center"][0]) ** 2
                    + (item["pixel"][1] - stone["pixel_center"][1]) ** 2
                ),
            )
            result = contact_below_cap(frames[row["time_s"]], candidate["pixel"])
            observations.append(
                {
                    "time_s": row["time_s"],
                    "cap_pixel": candidate["pixel"],
                    "contact_estimate": result,
                }
            )
        valid = [
            item["contact_estimate"]["pixel"]
            for item in observations
            if item["contact_estimate"] is not None
        ]
        if len(valid) < 3:
            raise ValueError("Insufficient stable body contacts")
        contacts.append(
            {
                "colour": stone["colour"],
                "cap_pixel_center": stone["pixel_center"],
                "contact_pixel_center": [
                    round(median(p[0] for p in valid), 2),
                    round(median(p[1] for p in valid), 2),
                ],
                "contact_supporting_frames": len(valid),
                "observations": observations,
            }
        )
    ellipse = wide["frames"][0]["ellipse"]
    cx, cy = ellipse["center_px"]
    rx = max(ellipse["axis_lengths_px"]) / 2
    ry = min(ellipse["axis_lengths_px"]) / 2
    yellow_contact = next(row for row in contacts if row["colour"] == "yellow")
    yellow_unflipped_y = (yellow_contact["contact_pixel_center"][1] - cy) / ry
    longitudinal_sign = (
        1
        if abs(yellow_unflipped_y - shared_yellow["longitudinal_house_radii"])
        < abs(-yellow_unflipped_y - shared_yellow["longitudinal_house_radii"])
        else -1
    )
    # A reversed camera axis predicts a 180-degree image orientation. The
    # shared near-centre yellow stone constrains y, but cannot independently
    # establish the lateral sign; keep both lateral alternatives for scoring.
    official = next(
        shot
        for game in json.loads(DIAGRAMS.read_text())["games"]
        for end in game["ends"]
        for shot in end["shots"]
        if shot["official_shot_id"] == SHOT_ID
    )
    alternatives = []
    for lateral_sign in (-1, 1):
        points = [
            {
                "colour": stone["colour"],
                "canonical_lateral_house_radii": round(
                    lateral_sign * (stone["contact_pixel_center"][0] - cx) / rx, 4
                ),
                "longitudinal_house_radii": round(
                    longitudinal_sign * (stone["contact_pixel_center"][1] - cy) / ry, 4
                ),
            }
            for stone in contacts
        ]
        alternatives.append(
            {
                "lateral_sign": lateral_sign,
                "orientation_status": (
                    "source_hypothesis_180_degree_view_reversal"
                    if lateral_sign == longitudinal_sign
                    else "unresolved_mirror_alternative"
                ),
                "source_only_coordinates": points,
                "strict_postscore": compare_board_observations(
                    points,
                    official["stones"],
                    official_house_center_y=official["house_center_px"][1],
                ),
                "forced_postscore": compare_board_observations(
                    points,
                    official["stones"],
                    official_house_center_y=official["house_center_px"][1],
                    max_match_distance=10,
                ),
            }
        )
    output = {
        "status": "postscore_wide_body_contact_development_diagnostic_not_board_export",
        "shot_id": SHOT_ID,
        "source_sha256": wide["source_sha256"],
        "wide_evidence_sha256": digest(WIDE),
        "close_video_board_sha256": digest(CLOSE),
        "official_diagrams_sha256": digest(DIAGRAMS),
        "contact_code_sha256": digest(ROOT / "prototype/wide_view_ground_contact.py"),
        "runner_sha256": digest(Path(__file__)),
        "source_only_shared_yellow_longitudinal_house_radii": shared_yellow[
            "longitudinal_house_radii"
        ],
        "wide_contact_unflipped_y_house_radii": round(yellow_unflipped_y, 4),
        "source_only_longitudinal_sign": longitudinal_sign,
        "contacts": contacts,
        "postscore_lateral_alternatives": alternatives,
        "limitations": [
            "The wide times were selected after an earlier China coverage failure.",
            "The body-bottom pixel approximates contact; no metric ice-plane calibration exists.",
            "The shared yellow stone gives a source-only y flip but not lateral orientation.",
            "Official positions score alternatives but do not choose any runtime orientation.",
            "No physical stone identity or simulation-ready state is exported.",
        ],
    }
    OUTPUT.write_text(json.dumps(output, indent=2) + "\n")
    print(
        {
            "contacts": [(s["colour"], s["contact_pixel_center"]) for s in contacts],
            "longitudinal_sign": longitudinal_sign,
            "strict_scores": [
                (a["lateral_sign"], a["strict_postscore"]["matched_count"]) for a in alternatives
            ],
        }
    )


if __name__ == "__main__":
    main()
