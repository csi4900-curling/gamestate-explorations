import math
import numpy as np
import pytest
from prototype.spin.signed_rotation import summarize


def test_one_turn_each_way_has_zero_net_and_two_total():
    t = np.arange(121)/30
    phase = np.where(t <= 2, math.pi*t, math.pi*(4-t))
    r = summarize(t, np.mod(phase, math.pi))
    assert r['signed_net_turns'] == pytest.approx(0, abs=1e-12)
    assert r['raw_total_variation_turns'] == pytest.approx(2)
    assert min(x['signed_delta_rad'] for x in r['samples'][1:]) < 0
    assert max(x['signed_delta_rad'] for x in r['samples'][1:]) > 0


def test_stop_and_reverse_does_not_require_monotonic_angles():
    t = np.arange(181)/30
    phase = np.piecewise(t, [t < 2, (t >= 2) & (t < 4), t >= 4],
                         [lambda x: math.pi*x, 2*math.pi, lambda x: math.pi*(6-x)])
    r = summarize(t, np.mod(phase, math.pi))
    assert r['signed_net_turns'] == pytest.approx(0, abs=1e-12)
    assert r['raw_total_variation_turns'] == pytest.approx(2)


def test_gap_does_not_hide_a_reversal_or_supply_whole_throw_total():
    r = summarize([0, .1, .2, .3, .4], [0, .1, None, .1, 0])
    assert len(r['groups']) == 2
    assert r['signed_net_turns'] is None
    assert r['raw_total_variation_turns'] is None
    assert r['samples'][3]['signed_delta_rad'] is None


def test_ambiguous_axial_sampling_splits_groups():
    r = summarize([0, 1], [0, .2])
    assert not r['complete_under_assumed_sampling_bound']
    assert r['samples'][1]['break_reason']


def test_reflection_reverses_net_but_preserves_distance():
    t = np.arange(31)/30
    a = summarize(t, t)
    b = summarize(t, -t)
    assert a['signed_net_turns'] == pytest.approx(-b['signed_net_turns'])
    assert a['raw_total_variation_turns'] == pytest.approx(b['raw_total_variation_turns'])


def test_invalid_time_rejected():
    with pytest.raises(ValueError):
        summarize([1, 1], [0, 1])
