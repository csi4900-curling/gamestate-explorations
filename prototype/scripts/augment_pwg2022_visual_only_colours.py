"""Add source-video post-cut colour evidence to all visual-only candidates."""

from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

import cv2


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from postcut_colour_support import resolve_postcut_colour
from scripts.audit_pwg2022_postcut_colour import scan_receiving_view
from scripts.audit_pwg2022_postcut_transfer import verified_cut

OUTPUT = ROOT / "validation/official-shot-sequence/pwg2022-visual-only-postcut-colours.json"
GAMES = (
    (
        "PREL000101",
        "validation/curlobserver-learned-probe/swiss-full-transfer/candidate-event-ledger.json",
        "validation/throw-event-benchmark/paralympics-2022-sweden-switzerland/source.mp4",
    ),
    (
        "PREL000102",
        "validation/curlobserver-learned-probe/china-full-transfer/candidate-throw-event-ledger-v1.json",
        "validation/throw-event-benchmark/paralympics-2022-canada-china/source.mp4",
    ),
    (
        "PREL000103",
        "validation/curlobserver-learned-probe/slovakia-full-transfer/candidate-event-ledger.json",
        "validation/throw-event-benchmark/paralympics-2022-slovakia-usa/source.mp4",
    ),
)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    if OUTPUT.exists():
        raise SystemExit("Output exists; preserve first visual-only colour augmentation")
    games = []
    for code, candidate_name, video_name in GAMES:
        candidate_path, video_path = ROOT / candidate_name, ROOT / video_name
        ledger = json.loads(candidate_path.read_text())
        if digest(video_path) != ledger["source_sha256"]:
            raise ValueError("Candidate ledger source hash mismatch")
        selected = [
            candidate
            for candidate in ledger["events"]
            if candidate["counter_id"] is None
            and candidate["evidence_class"] == "origin_view_candidate"
        ]
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            raise RuntimeError(f"Cannot open {video_path}")
        fps = cap.get(cv2.CAP_PROP_FPS)
        rows = []
        for candidate in selected:
            cut_s = candidate["release_window_s"][1]
            if not verified_cut(cap, fps, cut_s):
                decision = {"colour": None, "status": "unverified_cut"}
                counts = None
            else:
                tracks, _ = scan_receiving_view(cap, fps, cut_s)
                counts = {
                    colour: {
                        mode: sum(
                            item["camera_motion_status"] != "camera_explained_static"
                            for item in items
                        )
                        for mode, items in modes.items()
                    }
                    for colour, modes in tracks.items()
                }
                decision = resolve_postcut_colour(counts)
            rows.append(
                {
                    "candidate_id": candidate["candidate_id"],
                    "shot_id": candidate["shot_id"],
                    "release_window_s": candidate["release_window_s"],
                    "original_colour": candidate["colour"],
                    "postcut_colour": decision["colour"],
                    "postcut_status": decision["status"],
                    "postcut_track_counts_after_camera_filter": counts,
                    "colour_relation": (
                        "unchanged"
                        if decision["colour"] == candidate["colour"] and decision["colour"]
                        else "newly_resolved"
                        if decision["colour"] and candidate["colour"] is None
                        else "conflict"
                        if decision["colour"] and candidate["colour"] != decision["colour"]
                        else "abstained"
                    ),
                }
            )
        cap.release()
        games.append(
            {
                "official_game_code_for_join_only": code,
                "candidate_ledger_path": candidate_name,
                "candidate_ledger_sha256": digest(candidate_path),
                "source_video_path": video_name,
                "source_video_sha256": digest(video_path),
                "visual_only_candidate_count": len(rows),
                "postcut_status_counts": dict(Counter(row["postcut_status"] for row in rows)),
                "colour_relation_counts": dict(Counter(row["colour_relation"] for row in rows)),
                "rows": rows,
            }
        )
    output = {
        "status": "source_only_postcut_colour_sidecar_not_throw_confirmation",
        "scanner_code_sha256": digest(ROOT / "prototype/scripts/audit_pwg2022_postcut_colour.py"),
        "cut_check_code_sha256": digest(
            ROOT / "prototype/scripts/audit_pwg2022_postcut_transfer.py"
        ),
        "resolver_code_sha256": digest(ROOT / "prototype/postcut_colour_support.py"),
        "runner_sha256": digest(Path(__file__)),
        "official_reference_used_for_colour_decision": False,
        "games": games,
        "limitations": [
            "A resolved post-cut colour supports the receiving view; it does not establish stone identity across the cut or confirm a throw.",
            "These development candidate windows were selected by the existing detector, so this sidecar cannot measure missed throws or event F1.",
            "All original candidate colours remain preserved; this file only adds independently computed video-colour evidence.",
        ],
    }
    OUTPUT.write_text(json.dumps(output, indent=2) + "\n")
    for game in games:
        print(
            game["official_game_code_for_join_only"],
            game["postcut_status_counts"],
            game["colour_relation_counts"],
        )


if __name__ == "__main__":
    main()
