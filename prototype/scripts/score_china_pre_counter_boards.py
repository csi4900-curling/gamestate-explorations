"""Postscore the frozen wide-timing probe against current and prior boards."""

from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from prototype.board_state_comparison import compare_board_observations

BASE=ROOT/"validation/official-shot-sequence"
SCAN=BASE/"china-full-match-pre-counter-board-probe-first.json"
ALIGN=BASE/"pwg2022-official-counter-alignment.json"
DIAGRAMS=BASE/"pwg2022-official-board-diagrams.json"
OUTPUT=BASE/"china-full-match-pre-counter-board-first-score.json"


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def quality(comparison):
    return (comparison["matched_count"],
            -len(comparison["unmatched_video"])-len(comparison["unmatched_official"]),
            -(comparison["mean_matched_distance_house_radii"] or 0))


def main():
    if OUTPUT.exists():
        raise SystemExit("Output exists; preserve first timing-probe comparison")
    scan=json.loads(SCAN.read_text())
    alignment=json.loads(ALIGN.read_text())
    diagrams=json.loads(DIAGRAMS.read_text())
    game=next(g for g in alignment["games"] if g["official_game_code"]=="PREL000102")
    dg=next(g for g in diagrams["games"] if g["official_game_code"]=="PREL000102")
    if scan["source_video_sha256"]!=dg["source_video_sha256"]:
        raise ValueError("Source mismatch")
    counters={r["counter_id"]:r for r in game["counter_rows"]}
    shots={s["official_shot_id"]:s for e in dg["ends"] for s in e["shots"]}
    predecessor={}
    for end in dg["ends"]:
        for i,shot in enumerate(end["shots"]):
            predecessor[shot["official_shot_id"]]=end["shots"][i-1] if i else None
    rows=[]
    for observation in scan["rows"]:
        counter=counters[observation["counter_id"]]
        stones=observation["stable_partial_board"]
        row={"counter_id":observation["counter_id"],
             "counter_status":counter["status"],
             "official_shot_id":counter["official_shot_id"],
             "video_stone_count":len(stones),
             "accepted_frame_count":observation["accepted_frame_count"],
             "observation_interval_s":observation["observation_interval_s"]}
        if counter["status"] not in ("unique_colour_concordant",
                                     "unique_colour_concordant_amid_duplicate"):
            row["status"]="withheld_ambiguous_counter"
            rows.append(row)
            continue
        current=shots[counter["official_shot_id"]]
        current_score=compare_board_observations(stones,current["stones"],
            official_house_center_y=current["house_center_px"][1])
        prior=predecessor[current["official_shot_id"]]
        prior_score=compare_board_observations(stones,prior["stones"],
            official_house_center_y=prior["house_center_px"][1]) if prior else None
        relation=("prior_better" if prior_score and quality(prior_score)>quality(current_score)
                  else "current_better" if prior_score and quality(current_score)>quality(prior_score)
                  else "tied" if prior_score else "no_prior_shot_in_end")
        row.update({"status":"counter_order_proxy_comparison",
                    "official_symbol_count":len(current["stones"]),
                    "current_comparison":current_score,
                    "prior_official_shot_id":prior["official_shot_id"] if prior else None,
                    "prior_comparison":prior_score,
                    "current_vs_prior_quality":relation})
        rows.append(row)
    scored=[r for r in rows if r["status"]=="counter_order_proxy_comparison" and r["video_stone_count"]]
    result={"status":"first_postscore_pre_counter_timing_probe_not_promoted",
            "source_only_probe_sha256":digest(SCAN),
            "counter_alignment_sha256":digest(ALIGN),
            "official_diagrams_sha256":digest(DIAGRAMS),
            "comparator_sha256":digest(ROOT/"prototype/board_state_comparison.py"),
            "runner_sha256":digest(Path(__file__)),
            "counter_interval_count":len(rows),
            "scored_rows_with_video_board":len(scored),
            "scored_video_stone_count":sum(r["video_stone_count"] for r in scored),
            "current_matched_stone_count":sum(r["current_comparison"]["matched_count"] for r in scored),
            "current_complete_board_count":sum(r["video_stone_count"]==
                                                r["official_symbol_count"]==
                                                r["current_comparison"]["matched_count"] for r in scored),
            "prior_better_count":sum(r["current_vs_prior_quality"]=="prior_better" for r in scored),
            "current_better_count":sum(r["current_vs_prior_quality"]=="current_better" for r in scored),
            "tied_count":sum(r["current_vs_prior_quality"]=="tied" for r in scored),
            "rows":rows,
            "limitations":["This postscore comparison cannot establish physical throw boundaries or correct state timing from counter order alone.",
                           "Prior/current diagram agreement is a development diagnostic; quality ties do not prove either state.",
                           "The video-only probe remains frozen and unpromoted pending direct source-time validation."]}
    OUTPUT.write_text(json.dumps(result,indent=2)+"\n")
    print({key:result[key] for key in ("counter_interval_count","scored_rows_with_video_board",
                                     "scored_video_stone_count","current_matched_stone_count",
                                     "current_complete_board_count","prior_better_count",
                                     "current_better_count","tied_count")})


if __name__=="__main__":
    main()
