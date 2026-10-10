from copy import deepcopy
import json
from pathlib import Path

import pytest

from prototype.episode_state_timeline import build_episode_state_timeline


ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "validation/curlobserver-learned-probe"


def inputs():
    names = (
        "canada-latvia-2024-evidence-state-handoff-development.json",
        "canada-latvia-2024-partial-episode-union-development.json",
        "canada-latvia-2024-partial-episode-quiet-board-development.json",
        "canada-latvia-2024-partial-episode-board-comparisons-development.json",
    )
    return [json.loads((EVIDENCE / name).read_text()) for name in names]


def test_partial_episode_is_one_review_proposal_without_losing_candidates():
    result = build_episode_state_timeline(*inputs())
    assert len(result["candidate_timeline"]) == 27
    assert len(result["event_timeline"]) == 15
    assert [row["event_id"] for row in result["event_timeline"]][9:12] == [
        "S19", "P01", "S23"]
    grouped = [row["candidate_id"] for row in result["candidate_timeline"]
               if row["partial_episode_id"] == "P01"]
    assert grouped == ["S21", "S22"]
    partial = next(row for row in result["event_timeline"]
                   if row["event_id"] == "P01")
    assert partial["comparison_from_previous_accepted_event"]["status"] == \
        "abstain_intervening_passage_candidate"
    assert partial["comparison_to_next_accepted_event"]["status"] == \
        "view_local_partial_comparison"
    assert all(not row["simulation_ready"] and row["release_time_s"] is None
               for row in result["event_timeline"])


def test_frozen_accepted_event_cannot_be_reclassified_into_partial_episode():
    base, union, boards, comparisons = inputs()
    union = deepcopy(union)
    next(row for row in union["candidate_rows"] if row["candidate_id"] == "S19")[
        "partial_episode_id"] = "P01"
    with pytest.raises(ValueError, match="Frozen accepted event"):
        build_episode_state_timeline(base, union, boards, comparisons)


def test_neighbor_comparison_is_required_for_partial_state_handoff():
    base, union, boards, comparisons = inputs()
    comparisons = deepcopy(comparisons)
    comparisons["comparisons"] = comparisons["comparisons"][:1]
    with pytest.raises(ValueError, match="Missing neighboring board comparison"):
        build_episode_state_timeline(base, union, boards, comparisons)
