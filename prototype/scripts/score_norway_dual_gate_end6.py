"""Compare first end-6 mirrored-gate candidates with delayed counter proxies."""

from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from counter_proxy_event_score import score_visual_against_counters

BASE = ROOT / "validation/curlobserver-learned-probe/cap-patch-crossmatch-v1"
EVENTS = BASE / "norway-end6-dual-gate-events-first.json"
FIRST = ROOT / "validation/throw-event-benchmark/paralympics-2022-canada-norway/FIRST-TRANSFER.json"
OUTPUT = BASE / "norway-end6-dual-gate-counter-proxy-first.json"


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    if OUTPUT.exists():
        raise SystemExit("Output exists; preserve first end-6 counter comparison")
    event, first = (json.loads(path.read_text()) for path in (EVENTS, FIRST))
    if event["source_sha256"] != first["source_video_sha256"]:
        raise ValueError("Source mismatch")
    counters = [row for row in first["counter_alignment_rows"]
                if row["official_end"] == 6 and
                row["status"] in ("unique_colour_concordant",
                                  "unique_colour_concordant_amid_duplicate")]
    if len(counters) != 12:
        raise ValueError("Clean counter reference changed")
    visual = [{"shot_id": f"{row['shot_id']}-dual-gate",
               "interval_s": row["interval_s"], "colour": row["colour"]}
              for row in event["decisions"] if row["colour"] is not None]
    score = score_visual_against_counters(visual, counters)
    result = {
        "status": "first_end6_dual_gate_to_delayed_counter_proxy_not_physical_f1",
        "source_sha256": event["source_sha256"],
        "source_only_event_sha256": digest(EVENTS),
        "first_transfer_sha256": digest(FIRST),
        "scorer_sha256": digest(ROOT / "prototype/counter_proxy_event_score.py"),
        "runner_sha256": digest(Path(__file__)),
        "end": 6,
        "official_shot_count": 16,
        "clean_counter_count": len(counters),
        "score": score,
        "limitations": [
            "Delayed counter updates are weak references, with only 12 of 16 official shots covered.",
            "The visual components were developed on earlier ends of the same exposed match.",
            "Monotone timing can pair a visual cue with the wrong physical delivery.",
            "This is not complete-end or full-match physical throw precision, recall, F1, or exact release timing.",
        ],
    }
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n")
    print({name: score[name] for name in (
        "visual_candidate_count", "matched_count", "clean_counter_count",
        "known_colour_match_count", "known_colour_conflict_count",
        "counter_proxy_precision", "counter_proxy_recall")})
    print("unmatched visual", score["unmatched_visual_ids"])


if __name__ == "__main__":
    main()
