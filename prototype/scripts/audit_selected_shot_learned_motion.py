"""Run learned-box motion only where full-source cap evidence is uncertain."""

import argparse
import json
from math import ceil
from pathlib import Path
import sys

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cache_contract import file_sha256
from scripts.audit_full_shot_cap_motion import tracks_for_shot
from shot_motion_selection import selected_shot_indices
from stone_patch_detector import detect_stones, load_model


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--review", type=Path, required=True)
    parser.add_argument("--origins", type=Path, required=True)
    parser.add_argument("--cap-decisions", type=Path, required=True)
    parser.add_argument("--counter-alignment", type=Path, required=True)
    parser.add_argument("--fused-events", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists; preserve first selected learned-motion audit")
    manifest_path = args.review / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    origins = json.loads(args.origins.read_text())
    cap = json.loads(args.cap_decisions.read_text())
    counter = json.loads(args.counter_alignment.read_text())
    fused = json.loads(args.fused_events.read_text())
    digest = file_sha256(args.video)
    evidence = (manifest, origins, cap, counter, fused)
    if any(row["source_sha256"] != digest for row in evidence) or any(
            row["source_interval_s"] != manifest["source_interval_s"]
            for row in evidence):
        parser.error("Input source or interval fingerprints differ")
    if (cap["origins_sha256"] != file_sha256(args.origins) or
            counter["shot_score_sha256"] != file_sha256(args.origins) or
            fused["origins_sha256"] != file_sha256(args.origins)):
        parser.error("Derived inputs do not match these origin predictions")
    reserved = json.loads((ROOT / "validation/unseen-end/reservation.json").read_text())
    if digest == reserved["source_sha256"]:
        parser.error("Reserved independent source cannot be used for development")
    shots = manifest["shots"]
    if [row["id"] for row in shots] != [row["shot_id"] for row in origins["rows"]]:
        parser.error("Shot review and origin predictions differ")
    chosen = selected_shot_indices(origins["rows"], counter["rows"],
                                   cap["decisions"], fused["events"])
    chosen_set = set(chosen)
    model = load_model(args.model)
    capture = cv2.VideoCapture(str(args.video), cv2.CAP_FFMPEG,
                               [cv2.CAP_PROP_N_THREADS, 1])
    fps = capture.get(cv2.CAP_PROP_FPS)
    step = round(fps / 5)
    if fps <= 0 or step <= 0:
        parser.error("Unreadable video")
    by_shot = [[] for _ in shots]
    samples = 0
    for index in chosen:
        shot = shots[index]
        start, end = shot["interval_s"]
        first, last = ceil(start * fps), ceil(end * fps)
        capture.set(cv2.CAP_PROP_POS_FRAMES, first)
        observations = {"red": [], "yellow": []}
        for frame_index in range(first, last):
            if not capture.grab():
                raise RuntimeError(f"Decode failed at frame {frame_index}")
            if frame_index % step:
                continue
            ok, frame = capture.retrieve()
            if not ok:
                raise RuntimeError(f"Retrieve failed at frame {frame_index}")
            t = round(frame_index / fps, 3)
            for box in detect_stones(frame, model):
                x, y, width, height = box["bbox"]
                observations[box["colour"]].append((t, {
                    "pixel": [x + width / 2, y + height / 2],
                    "bbox": box["bbox"], "confidence": box["confidence"]}))
            samples += 1
        per_colour = {"red": [], "yellow": []}
        for colour in per_colour:
            grouped = {}
            for t, point in observations[colour]:
                grouped.setdefault(t, []).append(point)
            per_colour[colour] = sorted(grouped.items())
        by_shot[index] = tracks_for_shot(per_colour, shot["id"])
    capture.release()
    rows = []
    for index, shot in enumerate(shots):
        rows.append({"shot_id": shot["id"], "interval_s": shot["interval_s"],
                     "scanned": index in chosen_set,
                     "same_shot_candidates": by_shot[index],
                     "following_shot_id": shots[index + 1]["id"]
                     if index + 1 < len(shots) else None,
                     "following_shot_candidates": by_shot[index + 1]
                     if index + 1 < len(shots) else []})
    result = {"status": "development_selected_full_source_learned_motion_audit",
              "source_id": manifest["source_id"], "source_sha256": digest,
              "source_interval_s": manifest["source_interval_s"],
              "shot_manifest_sha256": file_sha256(manifest_path),
              "origins_sha256": file_sha256(args.origins),
              "cap_decisions_sha256": file_sha256(args.cap_decisions),
              "counter_alignment_sha256": file_sha256(args.counter_alignment),
              "fused_events_sha256": file_sha256(args.fused_events),
              "model_sha256": file_sha256(args.model),
              "feature_code_sha256": file_sha256(ROOT / "prototype/stone_patch_detector.py"),
              "selection_code_sha256": file_sha256(ROOT / "prototype/shot_motion_selection.py"),
              "tracking_code_sha256": file_sha256(ROOT / "prototype/stone_motion_fallback.py"),
              "runner_sha256": file_sha256(__file__),
              "selected_shot_count": len(chosen), "sample_count": samples,
              "sample_rate_hz": fps / step, "shots": rows,
              "limitations": [
                  "Only selected shots were scanned; an empty unscanned row is not negative evidence.",
                  "Selection uses exposed full-source cap and counter results, not labels.",
                  "Learned image boxes and tracks are not confirmed stone identities or throws.",
              ]}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"selected_shots": len(chosen), "samples": samples,
                      "tracks": sum(len(row) for row in by_shot)}))


if __name__ == "__main__":
    main()
