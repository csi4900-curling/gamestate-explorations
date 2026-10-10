"""Transfer a frozen one-frame right-cap continuation screen to another match."""

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import sys

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from right_colour_tail_screen import (predict_next_cap_center,
                                      screen_next_colour_frame)


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1048576), b""):
            h.update(chunk)
    return h.hexdigest()


def frame_at(cap, time_s):
    cap.set(cv2.CAP_PROP_POS_MSEC, time_s * 1000)
    ok, frame = cap.read()
    if not ok:
        raise ValueError(f"Source frame unavailable at {time_s} s")
    return frame


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("probe", "source-review", "lowres-video", "highres-video",
                 "output"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists")
    probe = json.loads(args.probe.read_text())
    review = json.loads(args.source_review.read_text())
    low_hash, high_hash = digest(args.lowres_video), digest(args.highres_video)
    if (low_hash != probe["source_sha256"] or
            low_hash != review["source_sha256"] or
            digest(args.probe) != review["probe_sha256"]):
        raise ValueError("Low-resolution source or review lineage differs")
    start, stop = probe["source_interval_s"]
    if [start, stop] != [1650, 2760]:
        raise ValueError("Unexpected transfer interval")
    proposals = probe["directional_review_proposals"]
    by_id = {row["raw_track_id"]: row for row in proposals}
    labels = {row["raw_track_id"]: row["source_prefix_class"] for row in
              review["rows"]}
    if (len(by_id) != len(proposals) or len(labels) != len(review["rows"])
            or set(by_id) != set(labels)):
        raise ValueError("Source review and proposal inventory differ")
    low = cv2.VideoCapture(str(args.lowres_video), cv2.CAP_FFMPEG,
                           [cv2.CAP_PROP_N_THREADS, 1])
    high = cv2.VideoCapture(str(args.highres_video), cv2.CAP_FFMPEG,
                            [cv2.CAP_PROP_N_THREADS, 1])
    if not low.isOpened() or not high.isOpened():
        raise RuntimeError("Could not open both recordings")
    try:
        alignment = []
        for time_s in (1700, 2000, 2300, 2600):
            low_frame = frame_at(low, time_s)
            high_frame = frame_at(high, time_s - start)
            if (low_frame.shape[:2] != (360, 640) or
                    high_frame.shape[:2] != (1080, 1920)):
                raise ValueError("Unexpected paired video resolution")
            small = cv2.resize(high_frame, (640, 360),
                               interpolation=cv2.INTER_AREA)
            left = cv2.cvtColor(low_frame, cv2.COLOR_BGR2GRAY).astype("float32")
            right = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY).astype("float32")
            correlation = float(np.corrcoef(left.ravel(), right.ravel())[0, 1])
            if correlation < 0.98:
                raise ValueError(f"Source excerpts misaligned at {time_s} s")
            alignment.append({"source_time_s": time_s,
                              "resized_frame_correlation": round(correlation, 6)})
        rows = []
        for proposal in proposals:
            points = proposal["observed_prefix_points"]
            last_time = points[-1]["time_s"]
            next_time = last_time + 1
            if not start <= next_time < stop:
                raise ValueError("Next frame outside high-resolution excerpt")
            predicted = predict_next_cap_center(points)
            frame = frame_at(high, next_time - start)
            screen = screen_next_colour_frame(frame, proposal["colour_claim"],
                                              predicted)
            rows.append({
                "raw_track_id": proposal["raw_track_id"],
                "source_prefix_class": labels[proposal["raw_track_id"]],
                "colour_claim": proposal["colour_claim"],
                "direction": proposal["direction"],
                "last_saved_cap_time_s": last_time,
                "last_saved_cap_center_360p_px": points[-1]["pixel"],
                "next_source_time_s": next_time,
                "predicted_cap_center_1080p_px": [round(v, 2) for v in predicted],
                "next_frame_screen": screen,
                "same_stone_identity_verified": False,
                "physical_throw_verified": False,
            })
    finally:
        low.release()
        high.release()
    counts = {label: dict(Counter(row["next_frame_screen"]["status"] for row
                                  in rows if row["source_prefix_class"] == label))
              for label in sorted(set(labels.values()))}
    output = {
        "status": "cross_recording_cap_tail_screen_development_not_event_accuracy",
        "source_sha256": {"lowres": low_hash, "highres": high_hash},
        "source_interval_s": [start, stop],
        "input_sha256": {"probe": digest(args.probe),
                         "source_review": digest(args.source_review)},
        "model_code_sha256": digest(ROOT / "prototype/right_colour_tail_screen.py"),
        "runner_sha256": digest(Path(__file__)),
        "alignment_check": alignment,
        "screen_rule": {"sample_offset_s": 1,
                        "area_px2": [200, 3500],
                        "maximum_prediction_distance_1080p_px": 30,
                        "source_cap_coordinate_scale": 3,
                        "ambiguity_policy": "abstain_unless_exactly_one_component"},
        "proposal_count": len(rows),
        "status_by_source_prefix_class": counts,
        "rows": rows,
        "limitations": [
            "Source classes were assigned by the detector developer on these exposed recordings.",
            "A same-colour next-frame component is not proven to be the same physical stone or a throw.",
            "The Latvia body-centered pilot and this cap-centered transfer use different seed coordinates.",
            "This is a one-second observability screen, not full path tracking or settled-state reconstruction.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps({"proposals": len(rows),
                      "status_by_class": counts}))


if __name__ == "__main__":
    main()
