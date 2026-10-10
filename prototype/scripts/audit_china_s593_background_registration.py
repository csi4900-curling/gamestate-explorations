"""Source-only audit of target-dominated camera registration at China S593."""

from hashlib import sha256
import json
from pathlib import Path
import sys

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from background_registration_audit import registration_support
from stone_motion_fallback import stone_cap_candidates

BASE = ROOT / "validation/official-shot-sequence"
HANDOFF = BASE / "pwg2022-two-view-temporal-handoff-development.json"
VIDEO = ROOT / "validation/throw-event-benchmark/paralympics-2022-canada-china/source.mp4"
OUTPUT = BASE / "china-s593-background-registration-development.json"


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def build():
    handoff = json.loads(HANDOFF.read_text())
    game = next(row for row in handoff["games"]
                if row["recording_code"] == "PREL000102")
    source_hash = digest(VIDEO)
    reserved = json.loads((ROOT / "validation/unseen-end/reservation.json").read_text())
    if source_hash != game["source_sha256"] or source_hash == reserved["source_sha256"]:
        raise ValueError("Source mismatch or reserved source")
    row = next(row for row in game["rows"] if row["event_id"] == "VISUAL-S593")
    time_s = row["first_receiving_motion_s"]
    times = [time_s, round(time_s + 1, 3)]
    capture = cv2.VideoCapture(str(VIDEO), cv2.CAP_FFMPEG,
                               [cv2.CAP_PROP_N_THREADS, 1])
    if not capture.isOpened():
        raise RuntimeError("Cannot open video")
    fps = capture.get(cv2.CAP_PROP_FPS)
    frames = []
    for t in times:
        capture.set(cv2.CAP_PROP_POS_FRAMES, round(t * fps))
        ok, frame = capture.read()
        if not ok:
            raise RuntimeError(f"Cannot decode {t}")
        frames.append(cv2.resize(frame, (640, 360), interpolation=cv2.INTER_AREA))
    capture.release()
    caps = stone_cap_candidates(frames[0], row["source_colour"])
    if len(caps) != 1:
        raise ValueError("Expected one yellow source cap in the selected frame")
    bbox = caps[0]["bbox"]
    return {"status": "postscore_selected_background_registration_diagnostic",
            "source_sha256": source_hash,
            "temporal_handoff_sha256": digest(HANDOFF),
            "audit_code_sha256": digest(ROOT / "prototype/background_registration_audit.py"),
            "original_camera_code_sha256": digest(ROOT / "prototype/camera_relative_motion.py"),
            "runner_sha256": digest(Path(__file__)),
            "event_id": row["event_id"],
            "source_colour": row["source_colour"],
            "frame_times_s": times,
            "target_cap_bbox_px": bbox,
            "unmasked": registration_support(*frames),
            "target_excluded": registration_support(*frames, exclude_bbox=bbox,
                                                     margin_px=30),
            "limitations": [
                "This pair was selected after S593 was identified as a source/ledger colour conflict; it is a diagnostic, not transfer validation.",
                "Feature support outside one stone does not by itself calibrate the camera or establish a full trajectory.",
                "No detector threshold, source colour, event identity, or physical F1 is changed.",
            ]}


def main():
    payload = json.dumps(build(), indent=2) + "\n"
    if OUTPUT.exists():
        if OUTPUT.read_text() != payload:
            raise SystemExit("Existing background audit differs from inputs or code")
        print(f"Verified {OUTPUT}")
    else:
        OUTPUT.write_text(payload)
        print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
