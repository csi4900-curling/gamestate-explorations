"""Render source-only right-panel samples for coarse windows missed by entry triage."""

import argparse
from hashlib import sha256
import json
from pathlib import Path

import cv2
import numpy as np


def digest(path):
    h = sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", required=True, type=Path)
    parser.add_argument("--transfer", required=True, type=Path)
    parser.add_argument("--reference", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    if args.output_dir.exists():
        parser.error("Output already exists")
    transfer = json.loads(args.transfer.read_text())
    reference = json.loads(args.reference.read_text())
    source_hash = digest(args.video)
    if source_hash != transfer["source_sha256"] or source_hash != reference["source_sha256"]:
        parser.error("Source fingerprints differ")
    entries = transfer["entry_review_proposals"]
    misses = [
        event
        for event in reference["events"]
        if not any(
            event["colour"] == row["colour_claim"]
            and event["delivery_interval_s"][0]
            <= row["entry_crossing"]["time_s"]
            <= event["delivery_interval_s"][1]
            for row in entries
        )
    ]
    cap = cv2.VideoCapture(str(args.video), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    if not cap.isOpened():
        parser.error("Unreadable video")
    fps = cap.get(cv2.CAP_PROP_FPS)
    args.output_dir.mkdir(parents=True)
    sheets = []
    try:
        for group_start in range(0, len(misses), 4):
            group = misses[group_start : group_start + 4]
            sheet = np.full((270 * len(group), 1600, 3), 25, dtype=np.uint8)
            for row_index, event in enumerate(group):
                lo, hi = event["delivery_interval_s"]
                # Five source-only samples spanning the coarse interval.
                times = np.linspace(lo, hi, 5)
                for col, t in enumerate(times):
                    cap.set(cv2.CAP_PROP_POS_FRAMES, round(float(t) * fps))
                    ok, frame = cap.read()
                    if not ok or frame.shape[1] < 640 or frame.shape[0] < 360:
                        raise RuntimeError(f"Could not decode split view at {t:.1f} s")
                    crop = frame[120:360, 320:640]
                    top, left = row_index * 270, col * 320
                    sheet[top + 30 : top + 270, left : left + 320] = crop
                    cv2.putText(
                        sheet,
                        f"{event['id']} {event['colour']} {t:.1f}s",
                        (left + 5, top + 21),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.48,
                        (255, 255, 255),
                        1,
                        cv2.LINE_AA,
                    )
            path = args.output_dir / f"sheet-{group_start // 4 + 1:02}.jpg"
            if not cv2.imwrite(str(path), sheet):
                raise RuntimeError(f"Could not write {path}")
            sheets.append(
                {
                    "file": path.name,
                    "sha256": digest(path),
                    "event_ids": [event["id"] for event in group],
                }
            )
    finally:
        cap.release()
    manifest = {
        "status": "source_samples_for_unmatched_coarse_windows_not_event_labels",
        "source_sha256": source_hash,
        "transfer_sha256": digest(args.transfer),
        "reference_sha256": digest(args.reference),
        "runner_sha256": digest(Path(__file__)),
        "missed_coarse_window_ids": [event["id"] for event in misses],
        "sheets": sheets,
        "limitations": [
            "Five sparse stills cannot establish the absence of a moving stone.",
            "The coarse reference is same-agent source-only development work, not independent exhaustive truth.",
        ],
    }
    (args.output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"unmatched_windows": len(misses), "sheets": len(sheets)}))


if __name__ == "__main__":
    main()
