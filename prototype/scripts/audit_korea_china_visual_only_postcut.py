"""Run the unchanged source-only post-cut colour diagnostic on new transfer extras."""

from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import sys

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from postcut_colour_support import resolve_postcut_colour  # noqa: E402
from scripts.audit_pwg2022_postcut_colour import scan_receiving_view  # noqa: E402
from scripts.audit_pwg2022_postcut_transfer import verified_cut  # noqa: E402

LEDGER = (
    ROOT
    / "validation/curlobserver-learned-probe/korea-china-full-first-transfer/candidate-event-ledger.json"
)
VIDEO = ROOT / "validation/throw-event-benchmark/paralympics-2022-korea-china/source.mp4"
OUTPUT = (
    ROOT / "validation/throw-event-benchmark/paralympics-2022-korea-china/VISUAL-ONLY-POSTCUT.json"
)


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    if OUTPUT.exists():
        raise SystemExit("Visual-only postcut audit already exists")
    ledger = json.loads(LEDGER.read_text())
    if digest(VIDEO) != ledger["source_sha256"]:
        raise ValueError("Source hash differs from frozen ledger")
    selected = [
        row
        for row in ledger["events"]
        if row["counter_id"] is None and row["evidence_class"] == "origin_view_candidate"
    ]
    cap = cv2.VideoCapture(str(VIDEO))
    if not cap.isOpened():
        raise RuntimeError("Cannot open source video")
    fps = cap.get(cv2.CAP_PROP_FPS)
    rows = []
    try:
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
    finally:
        cap.release()
    result = {
        "status": "postscore_source_only_visual_only_colour_diagnostic_not_throw_confirmation",
        "source_video_sha256": digest(VIDEO),
        "first_transfer_ledger_sha256": digest(LEDGER),
        "scanner_code_sha256": digest(ROOT / "prototype/scripts/audit_pwg2022_postcut_colour.py"),
        "cut_check_code_sha256": digest(
            ROOT / "prototype/scripts/audit_pwg2022_postcut_transfer.py"
        ),
        "resolver_code_sha256": digest(ROOT / "prototype/postcut_colour_support.py"),
        "runner_sha256": digest(Path(__file__)),
        "visual_only_candidate_count": len(rows),
        "postcut_status_counts": dict(Counter(row["postcut_status"] for row in rows)),
        "colour_relation_counts": dict(Counter(row["colour_relation"] for row in rows)),
        "rows": rows,
        "limitations": [
            "This is postscore development on an exposed transfer match; first predictions remain frozen.",
            "A resolved receiving-view colour does not verify stone identity across the cut or confirm a throw.",
            "Selected candidate windows cannot reveal missed physical throws or establish event F1.",
        ],
    }
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps(
            {
                k: result[k]
                for k in (
                    "visual_only_candidate_count",
                    "postcut_status_counts",
                    "colour_relation_counts",
                )
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
