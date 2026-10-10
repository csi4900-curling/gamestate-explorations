"""Probe unsupported interior Beijing gaps for unconfirmed stone motion."""

import argparse
import json
from pathlib import Path
import sys

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cache_contract import file_sha256
from gap_motion_candidates import candidates_from_observations, interior_beijing_gaps
from stone_motion_fallback import stone_cap_candidates


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--timeline", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--bright-body-probe",
        action="store_true",
        help="Development-only permissive cap proposals; never promotes gap events",
    )
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists; preserve prior diagnostic")
    source = json.loads(args.timeline.read_text())
    digest = file_sha256(args.video)
    if digest != source["source_sha256"]:
        parser.error("Video fingerprint differs from timeline")
    reserved = json.loads((ROOT / "validation/unseen-end/reservation.json").read_text())
    if digest == reserved["source_sha256"]:
        parser.error("This source is reserved for independent evaluation")
    # The timeline lists supported runs only; the hashed preflight holds the
    # complete partition including unknown spans.
    preflight_path = args.timeline.parent / "preflight.json"
    if not preflight_path.exists():
        parser.error("Missing preflight layout partition")
    if source.get("preflight_artifact_sha256") != file_sha256(preflight_path):
        parser.error("Preflight artifact differs from timeline provenance")
    preflight = json.loads(preflight_path.read_text())
    if preflight["source_sha256"] != digest:
        parser.error("Preflight fingerprint differs from timeline")
    gaps = interior_beijing_gaps(preflight["runs"])
    cap = cv2.VideoCapture(str(args.video), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0:
        raise ValueError("Unreadable video")
    all_candidates = []
    scanned = []
    for index, (start, end) in enumerate(gaps, 1):
        if int(start) != start or int(end) != end:
            raise ValueError("Gap probe requires integer-second boundaries")
        observations = {"red": [], "yellow": []}
        for t in range(int(start), int(end)):
            cap.set(cv2.CAP_PROP_POS_FRAMES, round(t * fps))
            ok, frame = cap.read()
            if not ok:
                cap.release()
                raise RuntimeError(f"Frame decode failed at {t} s")
            for colour in observations:
                observations[colour].append(
                    (
                        float(t),
                        stone_cap_candidates(
                            frame, colour, allow_bright_body=args.bright_body_probe
                        ),
                    )
                )
        gap_id = f"G{index:02}"
        candidates = candidates_from_observations(observations, gap_id, [start, end])
        all_candidates.extend(candidates)
        scanned.append(
            {
                "id": gap_id,
                "interval_s": [start, end],
                "samples": int(end - start),
                "candidate_count": len(candidates),
            }
        )
    cap.release()
    result = {
        "status": (
            "development_bright_body_gap_motion_probe"
            if args.bright_body_probe
            else "unconfirmed_gap_motion_probe"
        ),
        "bright_body_probe": args.bright_body_probe,
        "source_id": source["source_id"],
        "source_sha256": digest,
        "source_interval_s": source["source_interval_s"],
        "timeline_sha256": file_sha256(args.timeline),
        "model_sha256": file_sha256(ROOT / "prototype/gap_motion_candidates.py"),
        "visual_code_sha256": file_sha256(ROOT / "prototype/stone_motion_fallback.py"),
        "runner_sha256": file_sha256(__file__),
        "scanned_gaps": scanned,
        "motion_candidates": all_candidates,
        "candidate_count": len(all_candidates),
        "limitations": [
            "These are unconfirmed visual candidates and are not added to the event timeline or F1 score.",
            "Only unknown spans bracketed by Beijing-supported runs are scanned; opening and closing gaps are excluded.",
            "Camera cuts, occlusion and tracker fragmentation can miss or duplicate delivered stones.",
            "Observed visual track onset is not exact release time.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"scanned_gaps": len(scanned), "motion_candidates": len(all_candidates)}))


if __name__ == "__main__":
    main()
