"""Compare frozen end-3 visual transits with delayed counter proxies."""

from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from counter_proxy_event_score import score_visual_against_counters

BASE = ROOT / "validation/curlobserver-learned-probe/cap-patch-crossmatch-v1"
VISUAL = BASE / "norway-end3-short-transit-first.json"
FIRST = ROOT / "validation/throw-event-benchmark/paralympics-2022-canada-norway/FIRST-TRANSFER.json"
OUTPUT = BASE / "norway-end3-short-transit-counter-proxy.json"


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    if OUTPUT.exists():
        raise SystemExit("Output exists; preserve first counter-proxy comparison")
    visual = json.loads(VISUAL.read_text())
    first = json.loads(FIRST.read_text())
    if visual["source_sha256"] != first["source_video_sha256"]:
        raise ValueError("Video and counter references differ")
    counters = [
        row
        for row in first["counter_alignment_rows"]
        if row["official_end"] == 3
        and row["status"] in ("unique_colour_concordant", "unique_colour_concordant_amid_duplicate")
    ]
    if len(counters) != 14:
        raise ValueError("Clean counter reference changed")
    all_cues = []
    best_per_camera_shot = []
    for shot in visual["rows"]:
        for index, track in enumerate(shot["transits"], 1):
            row = {
                "shot_id": f"{shot['shot_id']}-T{index}",
                "camera_shot_id": shot["shot_id"],
                "interval_s": track["interval_s"],
                "colour": track["colour"],
                "point_count": track["point_count"],
                "displacement_px": track["displacement_px"],
            }
            all_cues.append(row)
            if index == 1:
                best_per_camera_shot.append(row)
    result = {
        "status": "development_end3_visual_to_delayed_counter_proxy_not_physical_event_f1",
        "source_sha256": visual["source_sha256"],
        "source_only_visual_sha256": digest(VISUAL),
        "first_transfer_sha256": digest(FIRST),
        "scorer_sha256": digest(ROOT / "prototype/counter_proxy_event_score.py"),
        "runner_sha256": digest(Path(__file__)),
        "end": 3,
        "camera_shot_count": visual["shot_count"],
        "clean_counter_count": len(counters),
        "all_visual_cues": all_cues,
        "all_cue_score": score_visual_against_counters(all_cues, counters),
        "best_per_camera_shot_cues": best_per_camera_shot,
        "best_per_camera_shot_score": score_visual_against_counters(best_per_camera_shot, counters),
        "limitations": [
            "Counter updates are delayed proxies, not independently labelled physical release times.",
            "The visual rule was chosen on exposed end-2 windows in the same match.",
            "Only 14 of 16 official end-3 shots have clean counter anchors; full-end recall is not measured.",
            "Monotone timing assignment may pair a visual cue with the wrong physical delivery, even when colour agrees.",
            "One cue per camera shot is a diagnostic deduplication, not a frozen event decision rule.",
        ],
    }
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n")
    for key in ("all_cue_score", "best_per_camera_shot_score"):
        score = result[key]
        print(
            key,
            {
                name: score[name]
                for name in (
                    "visual_candidate_count",
                    "matched_count",
                    "clean_counter_count",
                    "known_colour_match_count",
                    "known_colour_conflict_count",
                    "counter_proxy_precision",
                    "counter_proxy_recall",
                )
            },
        )


if __name__ == "__main__":
    main()
