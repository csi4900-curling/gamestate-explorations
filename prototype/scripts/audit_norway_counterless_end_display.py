"""Read source-video end labels near Norway candidates with no counter link.

The broadcast label is context, not an independently observed physical end.
Unknown and conflicting OCR results remain unknown.
"""

from hashlib import sha256
import json
from pathlib import Path
import re
import subprocess
import sys

import cv2


ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "validation/curlobserver-learned-probe/canada-norway-full-transfer"
VIDEO = ROOT / "validation/throw-event-benchmark/paralympics-2022-canada-norway/source.mp4"
EVENTS = BASE / "fused-linked.json"
SHOTS = BASE / "shot-review/manifest.json"
OUTPUT = ROOT / "validation/official-shot-sequence/norway-counterless-candidate-end-display-first.json"
PATTERN = re.compile(r"\b([1-8])\s*(?:ST|ND|RD|TH)\s*END\b")


def sha(path):
    return sha256(path.read_bytes()).hexdigest()


def read_label(frame):
    if frame is None:
        return {"text": None, "end": None}
    # Fixed 640x360 Beijing 2022 score graphic; its end text is below teams.
    frame = cv2.resize(frame, (640, 360), interpolation=cv2.INTER_AREA)
    crop = frame[54:71, 62:141]
    crop = cv2.resize(crop, None, fx=4, fy=4, interpolation=cv2.INTER_CUBIC)
    ok, encoded = cv2.imencode(".png", crop)
    if not ok:
        raise RuntimeError("Could not encode end-label crop")
    process = subprocess.run(["tesseract", "stdin", "stdout", "--psm", "7"],
                             input=encoded.tobytes(), capture_output=True, check=True)
    read = process.stdout.decode(errors="replace").strip().upper()
    match = PATTERN.search(read)
    return {"text": read, "end": int(match.group(1)) if match else None}


def main():
    if OUTPUT.exists():
        raise SystemExit("First OCR audit already exists")
    events = json.loads(EVENTS.read_text())
    manifest = json.loads(SHOTS.read_text())
    if len({events["source_sha256"], manifest["source_sha256"], sha(VIDEO)}) != 1:
        raise SystemExit("Source hashes disagree")
    shots = {row["id"]: row for row in manifest["shots"]}
    cap = cv2.VideoCapture(str(VIDEO))
    if not cap.isOpened():
        raise SystemExit("Cannot open source video")
    rows = []
    try:
        for event in events["events"]:
            if event["counter_id"] is not None:
                continue
            shot = shots[event["shot_id"]]
            observations = []
            for time_s in shot["frame_times_s"]:
                cap.set(cv2.CAP_PROP_POS_MSEC, 1000 * time_s)
                ok, frame = cap.read()
                observations.append({"time_s": time_s,
                                     **read_label(frame if ok else None)})
            hits = [row["end"] for row in observations if row["end"] is not None]
            stable_end = hits[0] if len(hits) >= 2 and len(set(hits)) == 1 else None
            rows.append({"shot_id": event["shot_id"],
                         "delivery_window_s": event["delivery_window_s"],
                         "candidate_colour": event["colour"],
                         "ocr_observations": observations,
                         "displayed_end": stable_end,
                         "display_status": "repeated_label" if stable_end else
                                           "unreadable_or_conflicting",
                         "physical_end": None})
    finally:
        cap.release()
    result = {
        "status": "source_broadcast_display_context_only",
        "source_video_sha256": sha(VIDEO),
        "input_sha256": {"candidate_ledger": sha(EVENTS), "shot_manifest": sha(SHOTS)},
        "runner_sha256": sha(Path(__file__)),
        "ocr_command": ["tesseract", "stdin", "stdout", "--psm", "7"],
        "candidate_count": len(rows),
        "stable_display_count": sum(row["displayed_end"] is not None for row in rows),
        "rows": rows,
        "limitations": [
            "The on-screen end can lag the first physical delivery of a new end.",
            "OCR is source-development evidence, not independently validated accuracy.",
            "An unreadable or conflicting display remains unknown; this audit does not fill official slots.",
        ],
    }
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n")
    print(result["candidate_count"], result["stable_display_count"])


if __name__ == "__main__":
    main()
