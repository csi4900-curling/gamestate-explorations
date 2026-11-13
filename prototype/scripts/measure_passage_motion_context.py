"""Measure local frame motion for each line-independent passage candidate."""

import argparse
import json
from pathlib import Path
import sys

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cache_contract import file_sha256
from passage_motion_context import motion_context_features


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--candidates", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists; preserve previous measurements")
    source = json.loads(args.candidates.read_text())
    if file_sha256(args.video) != source["source_sha256"]:
        parser.error("Video fingerprint does not match candidates")
    cap = cv2.VideoCapture(str(args.video), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0:
        raise ValueError("Unreadable video")

    def frame_at(t):
        cap.set(cv2.CAP_PROP_POS_FRAMES, round(t * fps))
        ok, frame = cap.read()
        if not ok:
            raise RuntimeError(f"Cannot decode {t:.3f} s")
        return frame

    rows = []
    for event in source["events"]:
        t = event["crossing_time_s"]
        before, after = frame_at(t - 0.25), frame_at(t + 0.25)
        rows.append(
            {
                "id": event["id"],
                "time_s": t,
                "x_px": event["crossing_x_px"],
                "y_px": event["passage_y_px"],
                **motion_context_features(
                    before, after, x=event["crossing_x_px"], y=event["passage_y_px"]
                ),
            }
        )
    cap.release()
    result = {
        "source_id": source["source_id"],
        "source_sha256": source["source_sha256"],
        "source_interval_s": source["source_interval_s"],
        "input_sha256": file_sha256(args.candidates),
        "feature_code_sha256": file_sha256(ROOT / "prototype/passage_motion_context.py"),
        "runner_sha256": file_sha256(__file__),
        "frame_offsets_s": [-0.25, 0.25],
        "rows": rows,
        "interpretation": "Pixel-change measurements only; neither object identity nor throw confirmation.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"measured": len(rows)}))


if __name__ == "__main__":
    main()
