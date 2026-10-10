"""Freeze a 16-shot Norway end-one sequence hypothesis without exact timing."""

from hashlib import sha256
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from prototype.end_sequence_hypothesis import build_first_end_hypothesis


BASE = ROOT / "validation/curlobserver-learned-probe/canada-norway-full-transfer"
CANDIDATES = BASE / "fused-linked.json"
COUNTERS = BASE / "counter-audit.json"
OFFICIAL = ROOT / "validation/official-shot-sequence/pwg2022-canada-norway-official-ledger.json"
GRAPH = ROOT / "validation/official-shot-sequence/norway-global-cap-motion-candidate-links-first.json"
RESCUES = ROOT / "validation/official-shot-sequence/norway-unlinked-motion-rescue-proposals-first.json"
OUTPUT = ROOT / "validation/official-shot-sequence/norway-end1-16-shot-sequence-hypothesis-first.json"


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    if OUTPUT.exists():
        raise SystemExit("Output exists; preserve first end-one sequence hypothesis")
    candidates = json.loads(CANDIDATES.read_text())
    counters = json.loads(COUNTERS.read_text())
    official = json.loads(OFFICIAL.read_text())
    graph = json.loads(GRAPH.read_text())
    rescues = json.loads(RESCUES.read_text())
    video_hashes = {candidates["source_sha256"], counters["source_sha256"],
                    official["source_video_sha256"]}
    if len(video_hashes) != 1:
        raise SystemExit("Inputs refer to different source videos")
    next_end = next(row for row in candidates["events"] if row["counter_id"] == "B16")
    rescue = [row for row in rescues["proposals"] if row["origin_shot_id"] == "S86"]
    if len(rescue) != 1 or rescue[0]["candidate_status"] != "origin_absent_from_candidate_ledger":
        raise SystemExit("S86 source-rescue proposal is missing or changed")
    hypothesis = build_first_end_hypothesis(
        candidates["events"], counters["counter_events"], official["ends"][0]["shots"],
        official["team_handle_colours"], graph, rescue[0],
        first_next_end_start_s=next_end["delivery_window_s"][0])
    if len(hypothesis["counterless_shared_motion_review"]) != 3 or any(
        not row["shared_with_counter_backed_candidates"]
        for row in hypothesis["counterless_shared_motion_review"]
    ):
        raise SystemExit("Unresolved extra candidate outside the expected shared-motion review")
    result = {
        "status": "development_norway_end1_16_shot_sequence_hypothesis_not_verified_video_f1",
        "input_sha256": {"candidate_ledger": digest(CANDIDATES),
                         "counter_audit": digest(COUNTERS),
                         "official_shot_ledger": digest(OFFICIAL),
                         "global_motion_candidate_graph": digest(GRAPH),
                         "unlinked_motion_rescue_proposals": digest(RESCUES)},
        "selection_code_sha256": digest(ROOT / "prototype/end_sequence_hypothesis.py"),
        "runner_sha256": digest(Path(__file__)),
        "first_next_end_candidate_shot_id": next_end["shot_id"],
        "first_next_end_candidate_start_s": next_end["delivery_window_s"][0],
        **hypothesis,
        "limitations": [
            "The official PDF gives order and colour, not video timestamps or identities.",
            "Broadcast counter decrements are delayed proxies, not observed release moments.",
            "Three counterless windows share motion with counter-backed candidates; that does not independently prove they are false events.",
            "The S86 rescue has source-compatible yellow origin/travel and official order, but cross-cut physical identity is unverified.",
            "Delivery windows are provisional; no exact release, settle, complete game state, or event F1 is established.",
        ],
    }
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n")
    print({"ordered_rows": len(result["rows"]),
           "counter_backed": result["counter_backed_candidate_count"],
           "shared_motion_extra_candidates": [row["candidate_shot_id"]
                                              for row in result["counterless_shared_motion_review"]],
           "final_source_rescue": result["rows"][-1]["video_candidate_shot_id"]})


if __name__ == "__main__":
    main()
