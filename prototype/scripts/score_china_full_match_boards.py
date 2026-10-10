"""Postscore the frozen source-only China board scan against official diagrams."""

from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from prototype.board_state_comparison import compare_board_observations

BASE=ROOT/"validation/official-shot-sequence"
SCAN=BASE/"china-full-match-source-video-boards-first.json"
ALIGN=BASE/"pwg2022-official-counter-alignment.json"
DIAGRAMS=BASE/"pwg2022-official-board-diagrams.json"
OUTPUT=BASE/"china-full-match-video-board-first-score.json"


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    if OUTPUT.exists():
        raise SystemExit("Output exists; preserve first full-match board comparison")
    scan=json.loads(SCAN.read_text())
    alignment=json.loads(ALIGN.read_text())
    diagrams=json.loads(DIAGRAMS.read_text())
    game=next(g for g in alignment["games"] if g["official_game_code"]=="PREL000102")
    diagram_game=next(g for g in diagrams["games"] if g["official_game_code"]=="PREL000102")
    if scan["source_video_sha256"]!=diagram_game["source_video_sha256"]:
        raise ValueError("Scan and official game source disagree")
    counters={r["counter_id"]:r for r in game["counter_rows"]}
    shots={s["official_shot_id"]:s for e in diagram_game["ends"] for s in e["shots"]}
    if len(counters)!=len(scan["rows"]) or len(shots)!=125:
        raise ValueError("Counter or official board count changed")
    rows=[]
    for observation in scan["rows"]:
        counter=counters[observation["counter_id"]]
        row={"counter_id":observation["counter_id"],"counter_status":counter["status"],
             "official_shot_id":counter["official_shot_id"],
             "video_stone_count":len(observation["stable_partial_board"]),
             "accepted_frame_count":observation["accepted_frame_count"]}
        if counter["status"] in ("unique_colour_concordant",
                                 "unique_colour_concordant_amid_duplicate"):
            shot=shots[counter["official_shot_id"]]
            comparison=compare_board_observations(observation["stable_partial_board"],
                                                   shot["stones"],
                                                   official_house_center_y=shot["house_center_px"][1])
            row.update({"comparison_status":"counter_order_proxy_comparison",
                        "official_symbol_count":len(shot["stones"]),
                        "comparison":comparison})
        else:
            row.update({"comparison_status":"withheld_ambiguous_counter",
                        "official_symbol_count":None,"comparison":None})
        rows.append(row)
    compared=[r for r in rows if r["comparison"] is not None]
    emitted=[r for r in compared if r["video_stone_count"]>0]
    result={"status":"first_postscore_china_full_match_board_development_comparison",
            "source_only_scan_sha256":digest(SCAN),
            "counter_alignment_sha256":digest(ALIGN),
            "official_diagrams_sha256":digest(DIAGRAMS),
            "comparator_sha256":digest(ROOT/"prototype/board_state_comparison.py"),
            "runner_sha256":digest(Path(__file__)),
            "counter_interval_count":len(rows),
            "counter_status_counts":dict(Counter(r["counter_status"] for r in rows)),
            "scored_counter_count":len(compared),
            "scored_rows_with_video_board":len(emitted),
            "scored_video_stone_count":sum(r["video_stone_count"] for r in emitted),
            "matched_stone_count":sum(r["comparison"]["matched_count"] for r in emitted),
            "complete_board_match_count":sum(r["video_stone_count"]==
                                              r["official_symbol_count"]==
                                              r["comparison"]["matched_count"] for r in emitted),
            "rows":rows,
            "limitations":["Source-video boards were frozen before PDF comparison, but the counter-to-official-shot alignment is a development proxy.",
                           "Only readable counter intervals were scanned; this is not 125/125 video game-state coverage.",
                           "A match to a diagram does not validate physical settle timing, persistent stone identity, metric scale, or a simulation-ready state."]}
    OUTPUT.write_text(json.dumps(result,indent=2)+"\n")
    print({key:result[key] for key in ("counter_interval_count","scored_counter_count",
                                     "scored_rows_with_video_board","scored_video_stone_count",
                                     "matched_stone_count","complete_board_match_count")})


if __name__=="__main__":
    main()
