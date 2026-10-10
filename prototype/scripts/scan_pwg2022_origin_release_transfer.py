"""Apply frozen held-cap release cue to all cap-unconfirmed 2022 origins."""

import hashlib
import json
from pathlib import Path
import sys

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from prototype.origin_release_passage import scan_origin_release

REFERENCE = ROOT / "validation/official-shot-sequence/pwg2022-official-shot-ledger.json"
OUTPUT = ROOT / "validation/official-shot-sequence/pwg2022-origin-release-transfer.json"
INPUTS = {
    "PREL000101": (
        "validation/curlobserver-learned-probe/swiss-full-transfer/shot-origin.json",
        "validation/curlobserver-learned-probe/swiss-full-transfer/two-shot-cap.json",
        "validation/curlobserver-learned-probe/swiss-full-transfer/hard-cuts.json",
    ),
    "PREL000102": (
        "validation/curlobserver-learned-probe/china-full-transfer/unlabelled-shot-origin-inference.json",
        "validation/curlobserver-learned-probe/china-full-transfer/two-shot-cap.json",
        "validation/curlobserver-learned-probe/china-full-transfer/hard-cuts.json",
    ),
    "PREL000103": (
        "validation/curlobserver-learned-probe/slovakia-full-transfer/shot-origin.json",
        "validation/curlobserver-learned-probe/slovakia-full-transfer/two-shot-cap.json",
        "validation/curlobserver-learned-probe/slovakia-full-transfer/hard-cuts.json",
    ),
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    if OUTPUT.exists():
        raise SystemExit("Output exists; preserve first frozen release transfer")
    reference = json.loads(REFERENCE.read_text())
    rows = []
    input_hashes = {}
    for game in reference["games"]:
        code = game["official_game_code"]
        origin_path, cap_path, cut_path = (ROOT / path for path in INPUTS[code])
        origins = json.loads(origin_path.read_text())
        cap_decisions = json.loads(cap_path.read_text())
        cuts = json.loads(cut_path.read_text())
        if cap_decisions["origins_sha256"] != digest(origin_path):
            raise ValueError(f"Cap provenance mismatch: {code}")
        if any(
            item["source_sha256"] != game["source_video_sha256"]
            for item in (origins, cap_decisions, cuts)
        ):
            raise ValueError(f"Source video provenance mismatch: {code}")
        input_hashes[code] = {
            "origin_sha256": digest(origin_path),
            "cap_decision_sha256": digest(cap_path),
            "hard_cuts_sha256": digest(cut_path),
            "source_video_sha256": game["source_video_sha256"],
        }
        decisions = {row["shot_id"]: row for row in cap_decisions["decisions"]}
        cut_times = [row["time_s"] for row in cuts["cuts"]]
        cap_video = cv2.VideoCapture(str(ROOT / game["source_video_path"]))
        if not cap_video.isOpened():
            raise RuntimeError(f"Cannot read {code} source")
        fps = cap_video.get(cv2.CAP_PROP_FPS)
        for origin in origins["rows"]:
            if (
                not origin["predicted"]
                or decisions[origin["shot_id"]]["status"] == "corroborated_candidate"
            ):
                continue
            start, end = origin["interval_s"]
            result = scan_origin_release(cap_video, fps, start, end, cut_times_s=cut_times)
            passages = result["passages"]
            rows.append(
                {
                    "official_game_code": code,
                    "shot_id": origin["shot_id"],
                    "origin_interval_s": origin["interval_s"],
                    "origin_probability": origin["probability"],
                    "cap_decision_reason": decisions[origin["shot_id"]]["reason"],
                    **result,
                    "unique_passage_colour": passages[0]["colour"] if len(passages) == 1 else None,
                }
            )
        cap_video.release()
    output = {
        "status": "frozen_origin_held_cap_release_transfer_development_not_event_f1",
        "official_reference_sha256": digest(REFERENCE),
        "input_hashes_by_game": input_hashes,
        "release_code_sha256": digest(ROOT / "prototype/origin_release_passage.py"),
        "cap_proposal_code_sha256": digest(ROOT / "prototype/stone_motion_fallback.py"),
        "runner_sha256": digest(Path(__file__)),
        "selection_rule": "All origin-predicted but cap-two-shot-unconfirmed shot windows in three full 2022 recordings; no official shot IDs, counters or colours select windows or set passage colour.",
        "release_rule": "At 5 Hz in lower delivery-side ice, a relaxed coloured cap with neutral/ice surround must remain within 8 px for at least 1.0 s, then travel at least 35 px within 1.6 s along one same-colour track; tracks cannot cross a hard broadcast cut. Exactly one passage resolves colour.",
        "scanned_window_count": len(rows),
        "windows_with_passage": sum(bool(row["passages"]) for row in rows),
        "windows_with_unique_passage_colour": sum(
            row["unique_passage_colour"] is not None for row in rows
        ),
        "rows": rows,
        "limitations": [
            "Thresholds were chosen after inspecting China end 4 missed deliveries; other 2022 windows test transfer only within the same production family.",
            "A held coloured cap can still belong to equipment or a non-delivered stone; this cue does not prove throw identity.",
            "Windows derive from an existing origin model and are not exhaustive full-video throw detections.",
            "No independent complete-recording precision or recall is estimated.",
        ],
    }
    OUTPUT.write_text(json.dumps(output, indent=2) + "\n")
    print(
        {
            key: output[key]
            for key in (
                "scanned_window_count",
                "windows_with_passage",
                "windows_with_unique_passage_colour",
            )
        }
    )
    for code in INPUTS:
        game_rows = [row for row in rows if row["official_game_code"] == code]
        print(code, len(game_rows), sum(bool(row["passages"]) for row in game_rows))


if __name__ == "__main__":
    main()
