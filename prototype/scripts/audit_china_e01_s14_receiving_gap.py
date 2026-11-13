"""Reproduce a selected receiving-only recall lead in China end one."""

from hashlib import sha256
import json
from pathlib import Path
import sys

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from prototype.scripts.audit_pwg2022_postcut_colour import scan_receiving_view
from prototype.scripts.audit_pwg2022_postcut_transfer import verified_cut

BASE = ROOT / "validation/official-shot-sequence"
QUEUE = BASE / "pwg2022-v3-sequence-review-queue-development.json"
UNASSIGNED = BASE / "pwg2022-all-unassigned-shots-PREL000102-source-scan-development.json"
MOTION = (
    ROOT
    / "validation/curlobserver-learned-probe/china-full-transfer/sequential-shot-cap-motion.json"
)
MANIFEST = (
    ROOT / "validation/curlobserver-learned-probe/china-full-transfer/shot-review/manifest.json"
)
VIDEO = ROOT / "validation/throw-event-benchmark/paralympics-2022-canada-china/source.mp4"
OUTPUT = BASE / "china-e01-s14-receiving-gap-development.json"


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def only(rows, key, value):
    found = [row for row in rows if row.get(key) == value]
    if len(found) != 1:
        raise ValueError(f"Expected one {key}={value}")
    return found[0]


def build():
    queue = json.loads(QUEUE.read_text())
    gap = only(queue["rows"], "official_shot_id", "PREL000102-E01-S14")
    source_scan = json.loads(UNASSIGNED.read_text())
    motion = json.loads(MOTION.read_text())
    manifest = json.loads(MANIFEST.read_text())
    source_hash = digest(VIDEO)
    if (
        source_hash != source_scan["source_sha256"]
        or source_hash != motion["source_sha256"]
        or source_hash != manifest["source_sha256"]
        or gap["source_video_path"] != str(VIDEO.relative_to(ROOT))
        or gap["preceding_matched_candidate_id"] != "VISUAL-S58"
        or gap["following_matched_candidate_id"] != "VISUAL-S66"
    ):
        raise ValueError("China E01-S14 source or bracket changed")
    shots = [only(manifest["shots"], "id", name) for name in ("S63", "S64", "S65")]
    if [row["interval_s"] for row in shots] != [[905.4, 915.4], [915.4, 928.4], [928.4, 932.2]]:
        raise ValueError("Selected camera-shot boundaries changed")
    origin_rows = [only(source_scan["rows"], "shot_id", name) for name in ("S63", "S64")]
    if (
        not origin_rows[0]["origin_model_predicted"]
        or origin_rows[1]["origin_model_predicted"]
        or any(row["raw_passages"] for row in origin_rows)
    ):
        raise ValueError("Selected origin scan changed")
    motion_row = only(motion["shots"], "shot_id", "S64")
    red_tracks = [row for row in motion_row["same_shot_candidates"] if row["colour"] == "red"]
    capture = cv2.VideoCapture(str(VIDEO), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    if not capture.isOpened():
        raise ValueError("Cannot open China source video")
    try:
        fps = capture.get(cv2.CAP_PROP_FPS)
        cut_verified = verified_cut(capture, fps, 915.4)
        tracks, further_cuts = scan_receiving_view(capture, fps, 915.4)
    finally:
        capture.release()
    strict_counts = {colour: len(modes["strict"]) for colour, modes in tracks.items()}
    if (
        not cut_verified
        or further_cuts
        or strict_counts != {"red": 0, "yellow": 0}
        or not red_tracks
    ):
        raise ValueError("Selected receiving-view diagnostic changed")
    return {
        "status": "development_selected_postscore_receiving_only_recall_lead_not_physical_f1",
        "official_gap_id_for_selection_only": gap["official_shot_id"],
        "source_sha256": source_hash,
        "input_sha256": {
            "sequence_queue": digest(QUEUE),
            "unassigned_shot_scan": digest(UNASSIGNED),
            "sequential_cap_motion": digest(MOTION),
            "shot_manifest": digest(MANIFEST),
            "postcut_scanner": digest(ROOT / "prototype/scripts/audit_pwg2022_postcut_colour.py"),
            "cut_check": digest(ROOT / "prototype/scripts/audit_pwg2022_postcut_transfer.py"),
            "runner": digest(Path(__file__)),
        },
        "bracketing_candidates": [
            gap["preceding_matched_candidate_id"],
            gap["following_matched_candidate_id"],
        ],
        "camera_shots": [{"shot_id": row["id"], "interval_s": row["interval_s"]} for row in shots],
        "origin_scan": [
            {
                "shot_id": row["shot_id"],
                "origin_model_predicted": bool(row["origin_model_predicted"]),
                "raw_passage_count": len(row["raw_passages"]),
            }
            for row in origin_rows
        ],
        "cut_at_915_4_s_verified": cut_verified,
        "s64_red_cap_track_summaries": red_tracks,
        "postcut_scan_window_s": [915.6, 927.4],
        "postcut_strict_track_counts": strict_counts,
        "postcut_relaxed_track_counts": {
            colour: len(modes["relaxed"]) for colour, modes in tracks.items()
        },
        "limitations": [
            "Official E01-S14 selected this postscore audit; it did not enter any video-only detector decision.",
            "The source frames show a red stone traveling in S64, but the release itself is hidden by a close-up and cut.",
            "A cap track or visual travel does not establish physical identity across views or prove an official-shot match.",
            "The current receiving-view scanner accepts no track here; camera following, cap fragmentation, and association ambiguity need separate diagnosis.",
        ],
    }


def main():
    payload = json.dumps(build(), indent=2) + "\n"
    if OUTPUT.exists() and OUTPUT.read_text() != payload:
        raise SystemExit("Existing selected gap diagnostic differs from hashed inputs")
    if not OUTPUT.exists():
        OUTPUT.write_text(payload)
    print(f"Verified {OUTPUT}")


if __name__ == "__main__":
    main()
