"""Apply the frozen shot-scoped release cue rule to Norway/China proposals."""

from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import sys

import cv2


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from prototype.origin_release_passage import scan_origin_release
from prototype.release_colour_review import classify_release_colour


SOURCES = {
    "norway": {
        "video": ROOT / "validation/throw-event-benchmark/paralympics-2022-canada-norway/source.mp4",
        "manifest": ROOT / "validation/curlobserver-learned-probe/canada-norway-full-transfer/shot-review/manifest.json",
        "proposals": ROOT / "validation/official-shot-sequence/norway-unlinked-motion-rescue-proposals-first.json",
    },
    "china": {
        "video": ROOT / "validation/throw-event-benchmark/paralympics-2022-canada-china/source.mp4",
        "manifest": ROOT / "validation/curlobserver-learned-probe/china-full-transfer/shot-review/manifest.json",
        "proposals": ROOT / "validation/official-shot-sequence/china-unlinked-motion-rescue-transfer-first.json",
    },
}
OUTPUT = ROOT / "validation/official-shot-sequence/unlinked-motion-release-colour-audit-first.json"


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    if OUTPUT.exists():
        raise SystemExit("Output exists; preserve first proposal release-colour audit")
    rows = []
    inputs = {}
    for game, paths in SOURCES.items():
        manifest = json.loads(paths["manifest"].read_text())
        proposals = json.loads(paths["proposals"].read_text())["proposals"]
        if digest(paths["video"]) != manifest["source_sha256"]:
            raise SystemExit(f"{game}: video does not match manifest")
        by_shot = {shot["id"]: shot["interval_s"] for shot in manifest["shots"]}
        capture = cv2.VideoCapture(str(paths["video"]))
        if not capture.isOpened():
            raise RuntimeError(f"Cannot open {game} source video")
        fps = capture.get(cv2.CAP_PROP_FPS)
        try:
            for proposal in proposals:
                shot_id = proposal["origin_shot_id"]
                start, end = proposal["origin_interval_s"]
                if by_shot[shot_id] != [start, end]:
                    raise SystemExit(f"{game}: origin interval changed for {shot_id}")
                scan = scan_origin_release(capture, fps, start, end)
                classification = classify_release_colour(
                    scan["passages"], proposal["receiving_colour"],
                    proposal["existing_candidate_colour"])
                rows.append({"game": game, "origin_shot_id": shot_id,
                             "origin_interval_s": [start, end],
                             "receiving_episode_id": proposal["receiving_episode_id"],
                             "receiving_colour": proposal["receiving_colour"],
                             "existing_candidate_colour": proposal["existing_candidate_colour"],
                             "sampled_frame_count": scan["sampled_frame_count"],
                             "filtered_cap_observation_count": scan["filtered_cap_observation_count"],
                             "shot_scoped_passages": scan["passages"],
                             **classification,
                             "physical_throw_verified": False})
        finally:
            capture.release()
        inputs[game] = {"video_sha256": digest(paths["video"]),
                        "camera_shot_manifest_sha256": digest(paths["manifest"]),
                        "proposal_sha256": digest(paths["proposals"])}
    result = {
        "status": "source_only_shot_scoped_release_colour_review_not_automatic_event_filter",
        "input_sha256": inputs,
        "release_detector_sha256": digest(ROOT / "prototype/origin_release_passage.py"),
        "cap_detector_sha256": digest(ROOT / "prototype/stone_motion_fallback.py"),
        "decision_code_sha256": digest(ROOT / "prototype/release_colour_review.py"),
        "runner_sha256": digest(Path(__file__)),
        "proposal_count": len(rows),
        "status_counts": dict(Counter(row["status"] for row in rows)),
        "rows": rows,
        "limitations": [
            "A held-to-motion cue is source-local colour evidence, not proof of cross-view stone identity or an exact physical release.",
            "No unique cue is an abstention, not evidence against a real throw.",
            "These proposals and thresholds were developed on exposed recordings; this is not independent precision/recall validation.",
            "No candidate is automatically accepted, rejected, inserted, or recoloured.",
        ],
    }
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n")
    print(result["status_counts"])
    print([(row["game"], row["origin_shot_id"], row["release_colour"])
           for row in rows if row["release_colour"]])


if __name__ == "__main__":
    main()
