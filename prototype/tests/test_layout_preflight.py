"""Fail-closed routing tests for changing or unsupported video layouts."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from layout_preflight import classify_chunk, split_2024_signature, summarize_evidence


def sample(t, *, split=False, beijing=False):
    return {
        "time_s": t,
        "split_2024_signature": split,
        "beijing_2022_counter": beijing,
    }


def test_stable_split_layout_routes():
    rows = [sample(t, split=True) for t in range(0, 600, 10)]
    result = summarize_evidence(rows, 0, 600)
    assert result["layout"] == "split_2024"
    assert len(result["chunks"]) == 2


def test_changing_layout_fails_closed():
    rows = [sample(t, split=t < 300, beijing=t >= 300) for t in range(0, 600, 10)]
    result = summarize_evidence(rows, 0, 600)
    assert result["layout"] == "unknown"
    assert [chunk["layout"] for chunk in result["chunks"]] == [
        "split_2024",
        "beijing_2022",
    ]
    assert result["runs"] == [
        {"layout": "split_2024", "interval_s": [0.0, 300.0], "samples": 30},
        {"layout": "beijing_2022", "interval_s": [300.0, 600], "samples": 30},
    ]
    assert result["coverage_gaps_s"] == []


def test_sparse_or_conflicting_evidence_is_unknown():
    assert classify_chunk([sample(t, split=True) for t in range(5)]) == "unknown"
    assert classify_chunk([sample(t, split=True, beijing=True) for t in range(8)]) == "unknown"


def test_single_dual_positive_digit_read_does_not_hide_stable_split_layout():
    rows = [sample(t, split=True, beijing=t == 0) for t in range(9)]
    assert classify_chunk(rows) == "split_2024"
    rows[0] = sample(0, split=False, beijing=True)
    assert classify_chunk(rows) == "unknown"


def test_strict_ice_geometry_allows_darker_2024_scoreboard():
    assert split_2024_signature(0.93, 0.90, 0.44)
    assert not split_2024_signature(0.79, 0.90, 0.44)
    assert not split_2024_signature(0.93, 0.84, 0.44)


def test_short_tail_is_merged_into_previous_chunk():
    rows = [sample(t, beijing=True) for t in range(0, 320, 10)]
    result = summarize_evidence(rows, 0, 320)
    assert result["layout"] == "beijing_2022"
    assert len(result["chunks"]) == 1


def test_unknown_gap_is_explicit_between_supported_runs():
    rows = [sample(t, split=t < 300 or t >= 600) for t in range(0, 900, 10)]
    result = summarize_evidence(rows, 0, 900)
    assert result["layout"] == "unknown"
    assert result["coverage_gaps_s"] == [[300.0, 600.0]]
    assert [row["layout"] for row in result["runs"]] == [
        "split_2024",
        "unknown",
        "split_2024",
    ]
