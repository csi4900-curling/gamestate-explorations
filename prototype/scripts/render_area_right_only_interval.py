"""Render all right-only proposals in a declared source interval."""

import argparse
from hashlib import sha256
import json
from pathlib import Path

import cv2
import numpy as np


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1048576), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("video", "probe", "episodes", "output-dir"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    parser.add_argument("--start", type=float, required=True)
    parser.add_argument("--stop", type=float, required=True)
    args = parser.parse_args()
    if args.output_dir.exists() or not args.start < args.stop:
        parser.error("Output directory exists or interval is invalid")
    probe, inventory = (json.loads(path.read_text()) for path in
                        (args.probe, args.episodes))
    source_hash = digest(args.video)
    if (probe["source_sha256"] != source_hash or
            inventory["source_sha256"] != source_hash or
            inventory["input_sha256"]["right"] != digest(args.probe)):
        raise ValueError("Source or episode lineage differs")
    tracks = {"R01:" + row["raw_track_id"]: row for row in
              probe["directional_review_proposals"]}
    selected = [row for row in inventory["episodes"]
                if row["episode_kind"] == "right_only_candidate" and
                args.start <= row["observation_time_s"] <= args.stop]
    if any(len(row["right_proposal_ids"]) != 1 or
           row["right_proposal_ids"][0] not in tracks for row in selected):
        raise ValueError("Right-only episode has missing or multiple tracks")
    cap = cv2.VideoCapture(str(args.video), cv2.CAP_FFMPEG,
                           [cv2.CAP_PROP_N_THREADS, 1])
    if not cap.isOpened():
        raise RuntimeError("Cannot open source video")
    fps = cap.get(cv2.CAP_PROP_FPS)
    args.output_dir.mkdir(parents=True)
    rows, sheets = [], []
    try:
        for start in range(0, len(selected), 4):
            group = selected[start:start + 4]
            sheet = np.full((360 * len(group), 960, 3), 25, dtype=np.uint8)
            for line, episode in enumerate(group):
                rid = episode["right_proposal_ids"][0]
                track = tracks[rid]
                points = track["observed_prefix_points"]
                event_time = track["passage"]["time_s"]
                chosen = [points[0], min(points, key=lambda point: abs(
                    point["time_s"] - event_time)), points[-1]]
                samples = []
                for col, point in enumerate(chosen):
                    frame_index = round((point["time_s"] -
                                         probe["source_time_offset_s"]) * fps)
                    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
                    ok, frame = cap.read()
                    if not ok or frame.shape[:2] != (360, 640):
                        raise RuntimeError(f"Cannot decode frame {frame_index}")
                    right = frame[:, 320:640].copy()
                    x, y, w, h = point["bbox"]
                    cv2.rectangle(right, (x - 320 - 2, y - 2),
                                  (x + w - 320 + 2, y + h + 2), (0, 255, 255), 2)
                    cv2.putText(right, f"{rid} {point['time_s']:.1f}s",
                                (4, 16), cv2.FONT_HERSHEY_SIMPLEX, .43,
                                (0, 0, 0), 3)
                    cv2.putText(right, f"{rid} {point['time_s']:.1f}s",
                                (4, 16), cv2.FONT_HERSHEY_SIMPLEX, .43,
                                (255, 255, 255), 1)
                    sheet[line * 360:(line + 1) * 360,
                          col * 320:(col + 1) * 320] = right
                    samples.append({"source_time_s": point["time_s"],
                                    "decoded_frame_index": frame_index,
                                    "pixel": point["pixel"],
                                    "bbox": point["bbox"]})
                rows.append({"episode_id": episode["episode_id"],
                             "right_proposal_id": rid,
                             "passage_time_s": event_time,
                             "colour_claim": track["colour_claim"],
                             "direction": track["direction"],
                             "sheet": f"sheet-{start // 4 + 1:02d}.jpg",
                             "samples": samples})
            path = args.output_dir / f"sheet-{start // 4 + 1:02d}.jpg"
            if not cv2.imwrite(str(path), sheet):
                raise RuntimeError(f"Cannot write {path}")
            sheets.append({"file": path.name, "sha256": digest(path),
                           "right_proposal_ids": [row["right_proposal_ids"][0]
                                                  for row in group]})
    finally:
        cap.release()
    manifest = {
        "status": "prediction_selected_source_frames_not_independent_throw_labels",
        "source_sha256": source_hash,
        "probe_sha256": digest(args.probe),
        "episodes_sha256": digest(args.episodes),
        "runner_sha256": digest(Path(__file__)),
        "selection": "all right-only episodes with passage in inclusive declared interval",
        "selection_interval_s": [args.start, args.stop],
        "rows": rows,
        "sheets": sheets,
        "limitations": [
            "Three sampled frames can identify a marked object but cannot verify a complete delivery.",
            "This is source review after proposal generation, not independent event validation.",
        ],
    }
    (args.output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"selected": len(rows), "sheets": len(sheets)}))


if __name__ == "__main__":
    main()
