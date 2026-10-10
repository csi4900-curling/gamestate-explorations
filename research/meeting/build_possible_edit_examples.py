"""Build two source-frame pairs for the possible-edit meeting figure."""

from hashlib import sha256
import json
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
VIDEO = ROOT / "validation/throw-event-benchmark/paralympics-2022-canada-china/source.mp4"
EDIT = ROOT / "validation/curlobserver-learned-probe/china-full-transfer/possible-edits-v1.json"
OUTPUT = Path(__file__).resolve().parent / "china-possible-edit-examples.jpg"
EXAMPLES = (("S123", 1606.0), ("S519", 7029.4))


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    edit = json.loads(EDIT.read_text())
    if digest(VIDEO) != edit["source_sha256"]:
        raise ValueError("Source fingerprint mismatch")
    proposed = {(row["shot_id"], row["time_s"])
                for row in edit["possible_edits_outside_hard_cuts"]}
    if not set(EXAMPLES) <= proposed:
        raise ValueError("Selected example disappeared from full scan")
    capture = cv2.VideoCapture(str(VIDEO), cv2.CAP_FFMPEG,
                               [cv2.CAP_PROP_N_THREADS, 1])
    fps = capture.get(cv2.CAP_PROP_FPS)
    rows = []
    for shot_id, time_s in EXAMPLES:
        cells = []
        for instant in (time_s - 0.2, time_s):
            capture.set(cv2.CAP_PROP_POS_FRAMES, round(instant * fps))
            ok, frame = capture.read()
            if not ok:
                raise RuntimeError(f"Frame decode failed at {instant}")
            frame = cv2.resize(frame, (480, 270), interpolation=cv2.INTER_AREA)
            label = f"{shot_id} / {instant:.1f} s"
            cv2.rectangle(frame, (0, 235), (480, 270), (12, 27, 35), -1)
            cv2.putText(frame, label, (12, 260), cv2.FONT_HERSHEY_SIMPLEX,
                        0.72, (255, 255, 255), 2, cv2.LINE_AA)
            cells.append(frame)
        rows.append(np.concatenate(cells, axis=1))
    capture.release()
    cv2.imwrite(str(OUTPUT), np.concatenate(rows, axis=0),
                [cv2.IMWRITE_JPEG_QUALITY, 87])
    print(OUTPUT)


if __name__ == "__main__":
    main()
