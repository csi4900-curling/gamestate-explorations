"""Combine cap, post-cut, and ice-gated origin passage visual cues."""

import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from prototype.counter_proxy_event_score import score_visual_against_counters

BASE = ROOT / "validation/official-shot-sequence/pwg2022-visual-counter-proxy.json"
POSTCUT = ROOT / "validation/official-shot-sequence/pwg2022-postcut-proxy-rescue.json"
PASSAGE = ROOT / "validation/official-shot-sequence/pwg2022-origin-release-ice-gate.json"
OUTPUT = ROOT / "validation/official-shot-sequence/pwg2022-combined-visual-counter-proxy.json"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    if OUTPUT.exists():
        raise SystemExit("Output exists; preserve first combined proxy audit")
    base, postcut, passage = (json.loads(path.read_text())
                              for path in (BASE, POSTCUT, PASSAGE))
    if postcut["proxy_sha256"] != digest(BASE):
        raise ValueError("Post-cut result derives from different base proxy")
    postcut_rows = {(row["official_game_code"], row["end"]): row
                    for row in postcut["rows"]}
    passage_rows = {(row["official_game_code"], row["shot_id"]): row
                    for row in passage["rows"]}
    rows = []
    for reference in base["rows"]:
        code, end = reference["official_game_code"], reference["end"]
        postcut_row = postcut_rows[code, end]
        chosen = {row["shot_id"]: row
                  for row in postcut_row["rescued_visual_candidates"]}
        passage_additions = []
        search_start, search_end = reference["visual_search_span_s"]
        for (passage_code, shot_id), item in passage_rows.items():
            if passage_code != code or item["unique_passage_colour"] is None:
                continue
            start = item["origin_interval_s"][0]
            if not search_start <= start <= search_end:
                continue
            if shot_id in chosen:
                # A contradictory source-only cue cannot change an already
                # emitted candidate's colour or create a duplicate event.
                continue
            candidate = {"shot_id": shot_id,
                         "interval_s": item["origin_interval_s"],
                         "colour": item["unique_passage_colour"]}
            chosen[shot_id] = candidate
            passage_additions.append(candidate)
        combined = sorted(chosen.values(), key=lambda row: row["interval_s"][0])
        score = score_visual_against_counters(combined, reference["clean_counters"])
        rows.append({"official_game_code": code, "end": end,
                     "base_score": reference["score"],
                     "postcut_score": postcut_row["postcut_score"],
                     "passage_additions": passage_additions,
                     "combined_visual_candidates": combined,
                     "combined_score": score})
    output = {
        "status": "in_sample_combined_visual_counter_proxy_ceiling_not_throw_f1",
        "base_proxy_sha256": digest(BASE),
        "postcut_sha256": digest(POSTCUT),
        "ice_gated_passage_sha256": digest(PASSAGE),
        "scorer_sha256": digest(ROOT / "prototype/counter_proxy_event_score.py"),
        "runner_sha256": digest(Path(__file__)),
        "rule": "Start from cap-confirmed visual candidates; add unique verified-cut post-cut motions for cap-unconfirmed positive origins; add unique ice-gated held-cap passages for remaining origin-positive windows. One shot ID may contribute at most one candidate; no counter or official colour enters selection.",
        "complete_end_count": len(rows),
        "base_total_matched": sum(row["base_score"]["matched_count"] for row in rows),
        "postcut_total_matched": sum(row["postcut_score"]["matched_count"] for row in rows),
        "combined_total_matched": sum(row["combined_score"]["matched_count"] for row in rows),
        "combined_visual_candidate_count": sum(row["combined_score"]["visual_candidate_count"] for row in rows),
        "clean_counter_count": sum(row["combined_score"]["clean_counter_count"] for row in rows),
        "rows": rows,
        "limitations": [
            "The held-cap passage and ice gate were selected after inspecting these China end-4 misses and a Swiss false positive; matching every clean counter here is in-sample development, not validated generalization.",
            "The broadcast counter is a delayed weak proxy, and broad timing windows can produce optimistic pairings.",
            "Other ends have incomplete counter coverage; no full-match precision, recall or release-time accuracy is measured.",
        ],
    }
    OUTPUT.write_text(json.dumps(output, indent=2) + "\n")
    print({key: output[key] for key in
           ("base_total_matched", "postcut_total_matched", "combined_total_matched",
            "combined_visual_candidate_count", "clean_counter_count")})


if __name__ == "__main__":
    main()
