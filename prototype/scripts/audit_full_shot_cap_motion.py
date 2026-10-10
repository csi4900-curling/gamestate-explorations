"""Scan one source sequentially for within-shot cap motion and adjacent support."""

import argparse
import json
from pathlib import Path
import sys

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cache_contract import file_sha256
from stone_motion_fallback import moving_cap_tracks, stone_cap_candidates


def tracks_for_shot(observations, shot_id):
    rows = []
    for colour in ("red", "yellow"):
        tracks = moving_cap_tracks(observations[colour], max_gap_s=1.6,
                                   max_step_px=130)
        for index, track in enumerate(tracks, 1):
            points = track["points"]
            rows.append({"id": f"{shot_id}-{colour[0].upper()}{index:02}",
                         "colour": colour,
                         "interval_s": [points[0]["time_s"], points[-1]["time_s"]],
                         "span_px": round(track["span_px"], 2),
                         "point_count": len(points)})
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--review", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists; preserve first full shot-motion audit")
    manifest_path = args.review / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    digest = file_sha256(args.video)
    if digest != manifest["source_sha256"] or args.source_id != manifest["source_id"]:
        parser.error("Source video or ID does not match shot manifest")
    reserved = json.loads((ROOT / "validation/unseen-end/reservation.json").read_text())
    if digest == reserved["source_sha256"]:
        parser.error("Reserved independent source cannot be used for development")
    shots = manifest["shots"]
    if not shots or any(a["interval_s"][1] != b["interval_s"][0]
                        for a, b in zip(shots, shots[1:])):
        parser.error("Shot manifest is empty or noncontiguous")
    begin, end = manifest["source_interval_s"]
    capture = cv2.VideoCapture(str(args.video), cv2.CAP_FFMPEG,
                               [cv2.CAP_PROP_N_THREADS, 1])
    fps = capture.get(cv2.CAP_PROP_FPS)
    step = round(fps / 5)
    if fps <= 0 or step <= 0 or shots[0]["interval_s"][0] != begin or (
            shots[-1]["interval_s"][1] != end):
        parser.error("Invalid video or shot interval")
    first, last = round(begin * fps), round(end * fps)
    capture.set(cv2.CAP_PROP_POS_FRAMES, first)
    by_shot = []
    observations = {"red": [], "yellow": []}
    index = 0
    samples = 0
    for frame_index in range(first, last):
        if not capture.grab():
            raise RuntimeError(f"Decode failed at frame {frame_index}")
        if (frame_index - first) % step:
            continue
        t = round(frame_index / fps, 3)
        while index + 1 < len(shots) and t >= shots[index]["interval_s"][1]:
            by_shot.append(tracks_for_shot(observations, shots[index]["id"]))
            observations = {"red": [], "yellow": []}
            index += 1
        ok, frame = capture.retrieve()
        if not ok:
            raise RuntimeError(f"Retrieve failed at frame {frame_index}")
        for colour in observations:
            observations[colour].append((t, stone_cap_candidates(
                frame, colour, allow_bright_body=True, allow_large_caps=True)))
        samples += 1
    capture.release()
    by_shot.append(tracks_for_shot(observations, shots[index]["id"]))
    while len(by_shot) < len(shots):
        by_shot.append([])
    rows = []
    for index, shot in enumerate(shots):
        rows.append({"shot_id": shot["id"], "interval_s": shot["interval_s"],
                     "same_shot_candidates": by_shot[index],
                     "following_shot_id": shots[index + 1]["id"]
                     if index + 1 < len(shots) else None,
                     "following_shot_candidates": by_shot[index + 1]
                     if index + 1 < len(shots) else []})
    result = {"status": "development_full_source_within_shot_cap_motion_audit",
              "source_id": args.source_id, "source_sha256": digest,
              "source_interval_s": [begin, end],
              "shot_manifest_sha256": file_sha256(manifest_path),
              "visual_code_sha256": file_sha256(ROOT / "prototype/stone_motion_fallback.py"),
              "runner_sha256": file_sha256(__file__),
              "sample_count": samples, "sample_rate_hz": fps / step,
              "shots": rows,
              "limitations": [
                  "Colour cap tracks can be people, graphics, moving old stones or camera motion.",
                  "Adjacent-shot colour agreement does not establish physical stone identity.",
                  "Short or slow tracks can be missed by the motion threshold.",
              ]}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"samples": samples, "shots": len(shots),
                      "tracks": sum(len(row) for row in by_shot)}))


if __name__ == "__main__":
    main()
