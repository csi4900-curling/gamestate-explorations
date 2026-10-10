from prototype.far_receiving_path import select_far_receiving_path


def sample(t, ys):
    return {
        "source_time_s": t,
        "corridor_candidate_count": len(ys),
        "corridor_candidates": [{"world_m": [0, y], "pixel": [0, 0]} for y in ys],
    }


def row(samples):
    return {
        "departure_last": {"time_s": 0, "world_m": [0, 0]},
        "arrival_first": {"time_s": 2, "world_m": [0, 4]},
        "samples": samples,
    }


def test_backward_outlier_is_not_selected():
    x = row([sample(0, [2, 9]), sample(1, [2.5]), sample(2, [4])])
    result = select_far_receiving_path(x)
    assert result["status"] == "unique_maximum_coverage_path_provisional"
    assert [n["world_m"][1] for n in result["path"]] == [2, 2.5, 4]
    assert result["discarded_candidate_count"] == 1


def test_equal_plausible_paths_abstain():
    x = row([sample(0, [0]), sample(1, [2, 2.1]), sample(2, [4])])
    result = select_far_receiving_path(x)
    assert result["status"] == "multiple_maximum_coverage_paths"
    assert result["path"] == []
