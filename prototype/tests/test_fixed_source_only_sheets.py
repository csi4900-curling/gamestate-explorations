from prototype.scripts.build_fixed_source_only_sheets import times_in_interval


def test_fixed_grid_excludes_interval_endpoint():
    times = times_in_interval(1650, 2760, 5)
    assert len(times) == 222
    assert times[0] == 1650
    assert times[-1] == 2755
