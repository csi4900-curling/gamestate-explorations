"""Run frozen held-cap plus ice-context rule on one 2022 recording."""

import argparse
import hashlib
import json
from pathlib import Path
import sys

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from prototype.origin_release_ice_support import passage_has_ice
from prototype.origin_release_passage import scan_origin_release


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--origins", type=Path, required=True)
    parser.add_argument("--cap-decisions", type=Path, required=True)
    parser.add_argument("--cuts", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists; preserve first frozen transfer")
    video_hash = digest(args.video)
    reserved = json.loads((ROOT / "validation/unseen-end/reservation.json").read_text())
    if video_hash == reserved["source_sha256"]:
        parser.error("Reserved independent source cannot be used for development")
    origins = json.loads(args.origins.read_text())
    decisions = json.loads(args.cap_decisions.read_text())
    cuts = json.loads(args.cuts.read_text())
    if decisions["origins_sha256"] != digest(args.origins):
        parser.error("Cap decisions use different origin rows")
    if any(row["source_sha256"] != video_hash for row in (origins, decisions, cuts)):
        parser.error("Input evidence uses a different source video")
    by_id = {row["shot_id"]: row for row in decisions["decisions"]}
    cut_times = [row["time_s"] for row in cuts["cuts"]]
    cap = cv2.VideoCapture(str(args.video))
    if not cap.isOpened():
        parser.error("Video cannot be opened")
    fps = cap.get(cv2.CAP_PROP_FPS)
    rows = []
    for origin in origins["rows"]:
        if (
            not origin["predicted"]
            or by_id[origin["shot_id"]]["status"] == "corroborated_candidate"
        ):
            continue
        start, end = origin["interval_s"]
        scan = scan_origin_release(cap, fps, start, end, cut_times_s=cut_times)
        accepted, rejected = [], []
        for passage in scan["passages"]:
            time_s = passage["held_interval_s"][0]
            cap.set(cv2.CAP_PROP_POS_FRAMES, round(time_s * fps))
            ok, frame = cap.read()
            if not ok:
                raise RuntimeError(f"Frame decode failed at {time_s}")
            supported, fraction = passage_has_ice(frame, passage)
            audited = {**passage, "held_frame_time_s": time_s, "below_ice_fraction": fraction}
            (accepted if supported else rejected).append(audited)
        rows.append(
            {
                "shot_id": origin["shot_id"],
                "origin_interval_s": origin["interval_s"],
                "origin_probability": origin["probability"],
                "cap_decision_reason": by_id[origin["shot_id"]]["reason"],
                "filtered_cap_observation_count": scan["filtered_cap_observation_count"],
                "accepted_passages": accepted,
                "rejected_passages": rejected,
                "unique_passage_colour": accepted[0]["colour"] if len(accepted) == 1 else None,
            }
        )
    cap.release()
    output = {
        "status": "frozen_2022_visual_origin_release_transfer_not_throw_f1",
        "source_sha256": video_hash,
        "source_interval_s": origins["source_interval_s"],
        "origins_sha256": digest(args.origins),
        "cap_decisions_sha256": digest(args.cap_decisions),
        "cuts_sha256": digest(args.cuts),
        "held_cap_code_sha256": digest(ROOT / "prototype/origin_release_passage.py"),
        "ice_context_code_sha256": digest(ROOT / "prototype/origin_release_ice_support.py"),
        "runner_sha256": digest(Path(__file__)),
        "selection_rule": "Every origin-predicted but cap-two-shot-unconfirmed shot interval; no counter, official shot, or colour label selects windows.",
        "scanned_window_count": len(rows),
        "accepted_window_count": sum(row["unique_passage_colour"] is not None for row in rows),
        "rejected_passage_count": sum(len(row["rejected_passages"]) for row in rows),
        "rows": rows,
        "limitations": [
            "This is a visual cue only; held equipment or clothing can still produce false passages.",
            "The source-specific lower-ice corridor assumes the Beijing 2022 delivery-view geometry.",
            "The originating shot model may omit deliveries, so this output alone cannot measure recall or full-video F1.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n")
    print(
        {
            key: output[key]
            for key in ("scanned_window_count", "accepted_window_count", "rejected_passage_count")
        }
    )


if __name__ == "__main__":
    main()
