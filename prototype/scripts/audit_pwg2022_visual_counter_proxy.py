"""Score pre-counter visual candidates on exhaustively counter-anchored ends."""

import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from prototype.counter_proxy_event_score import score_visual_against_counters

ALIGNMENT = ROOT / "validation/official-shot-sequence/pwg2022-official-counter-alignment.json"
REFERENCE = ROOT / "validation/official-shot-sequence/pwg2022-official-shot-ledger.json"
OUTPUT = ROOT / "validation/official-shot-sequence/pwg2022-visual-counter-proxy.json"
INPUTS = {
    "PREL000101": ("validation/curlobserver-learned-probe/swiss-full-transfer/shot-origin.json",
                   "validation/curlobserver-learned-probe/swiss-full-transfer/two-shot-cap.json"),
    "PREL000102": ("validation/curlobserver-learned-probe/china-full-transfer/unlabelled-shot-origin-inference.json",
                   "validation/curlobserver-learned-probe/china-full-transfer/two-shot-cap.json"),
    "PREL000103": ("validation/curlobserver-learned-probe/slovakia-full-transfer/shot-origin.json",
                   "validation/curlobserver-learned-probe/slovakia-full-transfer/two-shot-cap.json"),
}
CLEAN_STATUSES = {"unique_colour_concordant", "unique_colour_concordant_amid_duplicate"}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    if OUTPUT.exists():
        raise SystemExit("Output exists; preserve first counter-proxy audit")
    alignment = json.loads(ALIGNMENT.read_text())
    reference = json.loads(REFERENCE.read_text())
    if alignment["official_reference_sha256"] != digest(REFERENCE):
        raise ValueError("Official reference hash mismatch")
    by_alignment = {g["official_game_code"]: g for g in alignment["games"]}
    rows = []
    input_hashes = {}
    for game in reference["games"]:
        code = game["official_game_code"]
        origin_path, cap_path = (ROOT / path for path in INPUTS[code])
        origins, cap = json.loads(origin_path.read_text()), json.loads(cap_path.read_text())
        if cap["origins_sha256"] != digest(origin_path):
            raise ValueError(f"Visual decisions use different origin rows: {code}")
        if origins["source_sha256"] != game["source_video_sha256"] or cap["source_sha256"] != game["source_video_sha256"]:
            raise ValueError(f"Visual evidence uses different source video: {code}")
        input_hashes[code] = {"origin_path": INPUTS[code][0],
                              "origin_sha256": digest(origin_path),
                              "cap_decision_path": INPUTS[code][1],
                              "cap_decision_sha256": digest(cap_path)}
        origin_by_id = {row["shot_id"]: row for row in origins["rows"]}
        visual_all = [{"shot_id": decision["shot_id"],
                       "interval_s": origin_by_id[decision["shot_id"]]["interval_s"],
                       "colour": decision["colour"]}
                      for decision in cap["decisions"]
                      if decision["status"] == "corroborated_candidate"]
        alignment_game = by_alignment[code]
        for end in game["ends"]:
            counter_rows = [row for row in alignment_game["counter_rows"]
                            if row["official_end"] == end["end"]
                            and row["status"] in CLEAN_STATUSES]
            if len(counter_rows) != len(end["shots"]):
                continue
            times = [row["counter_time_s"] for row in counter_rows]
            first, last = min(times), max(times)
            visual = [row for row in visual_all
                      if first - 70 <= row["interval_s"][0] <= last]
            score = score_visual_against_counters(visual, counter_rows)
            rows.append({"official_game_code": code, "end": end["end"],
                         "counter_span_s": [first, last],
                         "visual_search_span_s": [first - 70, last],
                         "visual_candidates": visual,
                         "clean_counters": counter_rows,
                         "score": score})
    output = {
        "status": "complete_end_visual_to_counter_proxy_not_physical_throw_f1",
        "official_reference_sha256": digest(REFERENCE),
        "counter_alignment_sha256": digest(ALIGNMENT),
        "input_hashes_by_game": input_hashes,
        "scorer_sha256": digest(ROOT / "prototype/counter_proxy_event_score.py"),
        "runner_sha256": digest(Path(__file__)),
        "selection_rule": "Only ends where every official delivery has one clean colour-concordant counter anchor. Visual-only cap-confirmed shot candidates from first counter minus 70 seconds through last counter; no counter feature or official board position enters visual decision.",
        "matching_rule": "Monotone one-to-one: visual starts before counter, visual end at most 20 s after update, and update at most 50 s after visual end. Maximize match count, then known-colour agreements, then proximity to 15 s lag.",
        "complete_end_count": len(rows),
        "total_visual_candidates": sum(row["score"]["visual_candidate_count"] for row in rows),
        "total_clean_counters": sum(row["score"]["clean_counter_count"] for row in rows),
        "total_matched": sum(row["score"]["matched_count"] for row in rows),
        "rows": rows,
        "limitations": [
            "A broadcast decrement is delayed and is only a weak event proxy; it is not an independently labelled physical throw time.",
            "The two eligible complete ends are from the same development production family, and visual model selection used earlier development sources.",
            "The timing tolerance and broad release intervals can match the wrong nearby candidate; the score is an optimistic agreement diagnostic, not independent F1.",
            "Incomplete ends and all counter-unreadable shots are outside this audit, so full-match recall is not estimated.",
        ],
    }
    OUTPUT.write_text(json.dumps(output, indent=2) + "\n")
    print({key: output[key] for key in
           ("complete_end_count", "total_visual_candidates", "total_clean_counters", "total_matched")})
    for row in rows:
        print(row["official_game_code"], row["end"],
              {key: row["score"][key] for key in
               ("counter_proxy_precision", "counter_proxy_recall", "counter_proxy_f1")})


if __name__ == "__main__":
    main()
