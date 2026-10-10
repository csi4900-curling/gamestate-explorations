from copy import deepcopy

import pytest

from layout_gap_bridge import bridge_split_gaps


def example():
    chunks = [
        {"interval_s": [0, 90], "samples": 9, "split_signature_count": 9, "layout": "split_2024"},
        {"interval_s": [90, 180], "samples": 9, "split_signature_count": 4, "layout": "unknown"},
        {
            "interval_s": [180, 270],
            "samples": 9,
            "split_signature_count": 9,
            "layout": "split_2024",
        },
    ]
    samples = []
    for chunk in chunks:
        for n in range(9):
            samples.append(
                {
                    "time_s": chunk["interval_s"][0] + 10 * n,
                    "split_2024_signature": n < chunk["split_signature_count"],
                    "beijing_2022_counter": False,
                }
            )
    return {
        "layout_chunk_s": 90,
        "chunks": chunks,
        "samples": samples,
        "layout": "unknown",
        "runs": [],
        "coverage_gaps_s": [[90, 180]],
    }


def test_bridges_only_supported_isolated_gap_without_changing_source():
    source = example()
    frozen = deepcopy(source)
    result = bridge_split_gaps(source)
    assert source == frozen
    assert result["bridge_promoted_intervals_s"] == [[90, 180]]
    assert result["runs"] == [{"layout": "split_2024", "interval_s": [0, 270], "samples": 27}]
    assert result["coverage_gaps_s"] == []


def test_does_not_bridge_beijing_conflict_or_unbracketed_gap():
    source = example()
    source["samples"][13]["beijing_2022_counter"] = True
    source["samples"][14]["beijing_2022_counter"] = True
    assert bridge_split_gaps(source)["bridge_promoted_intervals_s"] == []
    source = example()
    source["chunks"][2]["layout"] = "unknown"
    assert bridge_split_gaps(source)["bridge_promoted_intervals_s"] == []


def test_rejects_other_chunk_resolution():
    source = example()
    source["layout_chunk_s"] = 300
    with pytest.raises(ValueError):
        bridge_split_gaps(source)
