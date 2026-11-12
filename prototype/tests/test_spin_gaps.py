import math
import json
import numpy as np
import pytest
from prototype.spin.gaps import GapConfig, reconstruct, evaluate_hidden_intervals


def fixture(rate=1.3):
    t = np.arange(0, 4.01, 1/30)
    angle = (2.9 + rate*t + math.pi) % (2*math.pi) - math.pi
    visible = ~((t >= 1.2) & (t <= 1.8))
    return t, angle, visible


def test_exact_reconnection_preserves_measurements_and_counts_wrap():
    t, a, v = fixture()
    r = reconstruct(t, a, v)
    assert r['estimated_count'] == (~v).sum()
    assert r['unresolved_count'] == 0
    assert r['gaps'][0]['candidate_turn_offsets'] == [1]
    assert r['signed_turns_over_input_interval'] == pytest.approx(1.3 * 4 / (2*math.pi))
    assert [s['observed_angle_rad'] for s in r['samples'] if s['status']=='observed'] == list(a[v])
    assert all(s['observed_angle_rad'] is None for s in r['samples'] if s['status']=='estimated')
    json.dumps(r, allow_nan=False)
    json.dumps(evaluate_hidden_intervals(t,a,np.ones(len(t),bool),[(1.2,1.8)]), allow_nan=False)


def test_negative_rotation_and_pi_symmetric_handle():
    t, a, v = fixture(-1.1)
    r = reconstruct(t, np.mod(a, math.pi), v, GapConfig(period_rad=math.pi))
    assert r['signed_turns_over_input_interval'] == pytest.approx(-1.1 * 4 / (2*math.pi))


def test_changed_rate_does_not_get_forced_to_match():
    t,a,v=fixture()
    a[t>1.8] += (t[t>1.8]-1.8)*1.5
    r=reconstruct(t,a,v)
    assert r['gaps'][0]['reason']=='angular_velocity_changed_across_gap'
    assert r['signed_turns_over_input_interval'] is None


def test_whole_turn_ambiguity_is_explicit():
    t,a,v=fixture()
    r=reconstruct(t,a,v,GapConfig(rate_tolerance_rad_s=12, max_abs_rate_rad_s=12))
    assert r['gaps'][0]['reason']=='ambiguous_turn_count'
    assert len(r['gaps'][0]['candidate_turn_offsets']) > 1
    assert r['estimated_count']==0


def test_known_collision_never_smoothed():
    t,a,v=fixture()
    r=reconstruct(t,a,v,breaks=[1.5])
    assert r['gaps'][0]['reason']=='known_collision_or_camera_break'
    assert r['estimated_count']==0


def test_no_extrapolation_before_or_after_observations():
    t,a,v=fixture()
    v[:10]=False;v[-10:]=False
    r=reconstruct(t,a,v)
    assert all(s['status']=='unresolved' for s in r['samples'][:10]+r['samples'][-10:])
    assert r['signed_turns_over_input_interval'] is None


def test_hidden_reference_not_used_to_fit_and_wrong_turns_not_hidden_by_wrapping():
    t,a,_=fixture()
    visible=np.ones(len(t),bool)
    intervals=[(1.2,1.8)]
    baseline=evaluate_hidden_intervals(t,a,visible,intervals)
    changed=a.copy();changed[(t>=1.2)&(t<=1.8)]+=0.4
    trial=evaluate_hidden_intervals(t,changed,visible,intervals)
    assert baseline[0]['gaps']==trial[0]['gaps']
    assert baseline[0]['wrapped_angle_mae_deg'] < 1e-8
    assert trial[0]['wrapped_angle_mae_deg']==pytest.approx(np.degrees(0.4))


def test_sampling_alias_no_total_claim():
    t=np.array([0.,2.,4.]);a=np.array([0.,1.,2.]);v=np.ones(3,bool)
    r=reconstruct(t,a,v)
    assert not r['sampling_unaliased_under_configured_max_rate']
    assert r['signed_turns_over_input_interval'] is None


def test_nonfinite_and_nonmonotonic_inputs_rejected():
    with pytest.raises(ValueError):reconstruct([0,0],[0,1],[True,True])
    with pytest.raises(ValueError):reconstruct([0,1],[0,float('nan')],[True,True])


def test_all_missing_stays_unknown():
    r=reconstruct([0,1],[float('nan')]*2,[False,False])
    assert r['unresolved_count']==2 and r['signed_turns_over_input_interval'] is None
