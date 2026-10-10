"""Audit unique source-colour motion approaches near stable Norway boards."""

from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import sys

import cv2


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from prototype.motion_approach_orientation import approach_direction
from prototype.video_board_observation_v2 import detect_overhead_house


BASE = ROOT / "validation/official-shot-sequence"
SCAN = BASE / "norway-full-candidate-post-window-image-boards-v2.json"
LINKS = BASE / "norway-global-cap-motion-candidate-links-first.json"
CATALOG = BASE / "norway-global-shot-scoped-cap-motion-first.json"
VIDEO = ROOT / "validation/throw-event-benchmark/paralympics-2022-canada-norway/source.mp4"
OUTPUT = BASE / "norway-motion-approach-orientation-cues-first.json"


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    if OUTPUT.exists():
        raise SystemExit("First motion-approach audit already exists")
    scan = json.loads(SCAN.read_text())
    links = json.loads(LINKS.read_text())
    catalog = json.loads(CATALOG.read_text())
    source_hash = digest(VIDEO)
    if len({scan["source_video_sha256"], catalog["source_video_sha256"], source_hash}) != 1:
        raise SystemExit("Source hashes disagree")
    if links["global_motion_catalog_sha256"] != digest(CATALOG):
        raise SystemExit("Link/catalog hash conflict")
    by_link = {row["candidate_id"]: row for row in links["candidates"]}
    by_track = {track["episode_id"]: track for shot in catalog["shots"] for track in shot["tracks"]}
    if len(by_track) != catalog["episode_count"]:
        raise SystemExit("Duplicate catalogue episode IDs")
    cap = cv2.VideoCapture(str(VIDEO))
    if not cap.isOpened():
        raise SystemExit("Cannot open video")
    rows = []
    try:
        for candidate in scan["rows"]:
            for group in candidate["camera_shot_boards"]:
                stable = group["stable_image_relative_stones"]
                if not stable:
                    continue
                row = {"candidate_id": candidate["shot_id"],
                       "camera_shot_id": group["camera_shot_id"],
                       "candidate_source_colour": candidate["candidate_colour"],
                       "layout_side": group["detected_delivery_side"],
                       "stable_stone_count": len(stable),
                       "proposed_delivery_side": None,
                       "status": None}
                if candidate["candidate_colour"] is None:
                    row["status"] = "abstain_candidate_colour_unknown"
                    rows.append(row)
                    continue
                matched = [by_track[episode_id] for episode_id in
                           by_link[candidate["shot_id"]]["exclusive_episode_ids"]
                           if episode_id in by_track and
                           by_track[episode_id]["camera_shot_id"] == group["camera_shot_id"] and
                           by_track[episode_id]["colour"] == candidate["candidate_colour"]]
                row["eligible_exclusive_track_ids"] = [track["episode_id"] for track in matched]
                if len(matched) != 1:
                    row["status"] = "abstain_no_unique_matching_exclusive_track"
                    rows.append(row)
                    continue
                track = matched[0]
                time_s = group["observation_interval_s"][0]
                cap.set(cv2.CAP_PROP_POS_MSEC, time_s * 1000)
                ok, frame = cap.read()
                house = detect_overhead_house(frame) if ok else None
                if house is None:
                    row["status"] = "abstain_house_not_reproduced"
                    rows.append(row)
                    continue
                stable_first = min(stone["first_seen_s"] for stone in stable)
                cue = approach_direction(track["first_pixel"], track["last_pixel"],
                                         house["center_px"][1], track["interval_s"][1],
                                         stable_first)
                row.update({"track_id": track["episode_id"],
                            "track_colour": track["colour"],
                            "track_interval_s": track["interval_s"],
                            "first_pixel": track["first_pixel"],
                            "last_pixel": track["last_pixel"],
                            "house_measurement_time_s": time_s,
                            "house_center_y_px": house["center_px"][1],
                            "first_stable_stone_s": stable_first,
                            **cue})
                row["status"] = ("source_motion_approach_proposal" if cue["proposed_delivery_side"]
                                 else "abstain_motion_not_clear_approach")
                rows.append(row)
    finally:
        cap.release()
    proposed = [row for row in rows if row["proposed_delivery_side"]]
    result = {
        "status": "source_only_development_orientation_cue_audit_not_physical_identity_validation",
        "source_video_sha256": source_hash,
        "input_sha256": {"image_board_scan": digest(SCAN), "candidate_motion_links": digest(LINKS),
                         "global_motion_catalog": digest(CATALOG)},
        "cue_code_sha256": digest(ROOT / "prototype/motion_approach_orientation.py"),
        "house_detector_sha256": digest(ROOT / "prototype/video_board_observation_v2.py"),
        "runner_sha256": digest(Path(__file__)),
        "stable_camera_group_count": len(rows),
        "status_counts": dict(Counter(row["status"] for row in rows)),
        "proposed_side_count": len(proposed),
        "proposals_with_known_layout_agreement": sum(row["layout_side"] == row["proposed_delivery_side"]
                                                      for row in proposed if row["layout_side"]),
        "proposals_with_known_layout_conflict": sum(row["layout_side"] != row["proposed_delivery_side"]
                                                     for row in proposed if row["layout_side"]),
        "proposals_with_unknown_layout": sum(row["layout_side"] is None for row in proposed),
        "rows": rows,
        "limitations": [
            "Exclusive catalogue tracks are not verified delivered-stone identities.",
            "A camera can pan between track endpoints and the later house measurement; direction is a proposal.",
            "The view-layout side is itself a proxy, not independent physical ground truth.",
            "Thresholds and source were examined in development; no unseen-video accuracy is inferred.",
        ],
    }
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n")
    print({key: result[key] for key in
           ("stable_camera_group_count", "proposed_side_count",
            "proposals_with_known_layout_agreement", "proposals_with_known_layout_conflict",
            "proposals_with_unknown_layout")})


if __name__ == "__main__":
    main()
