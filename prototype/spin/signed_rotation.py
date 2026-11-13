"""Accumulate observed axial orientations without a preferred rotation direction.

No gap filling, extrapolation or physics-derived angular observations. Total
variation includes measurement jitter and is not automatically physical rotation.
"""
import math
import numpy as np


def summarize(times, angles, *, period_rad=math.pi, max_abs_rate_rad_s=6.0):
    t = np.asarray(times, float)
    a = np.asarray([np.nan if x is None else x for x in angles], float)
    if t.ndim != 1 or not len(t) or t.shape != a.shape:
        raise ValueError('Nonempty matching time and angle vectors required')
    if not np.isfinite(t).all() or np.any(np.diff(t) <= 0):
        raise ValueError('Finite strictly increasing times required')
    if not math.isfinite(period_rad) or period_rad <= 0:
        raise ValueError('Positive finite orientation period required')
    if not math.isfinite(max_abs_rate_rad_s) or max_abs_rate_rad_s <= 0:
        raise ValueError('Positive finite assumed maximum rate required')
    samples, groups = [], []
    previous = None
    for i, (ti, ai) in enumerate(zip(t, a)):
        row = {'time_s': float(ti), 'angle_rad': float(ai) if np.isfinite(ai) else None,
               'signed_delta_rad': None, 'phase_rad': None, 'phase_group': None}
        if not np.isfinite(ai):
            previous = None
            samples.append(row)
            continue
        if previous is not None:
            dt = ti-t[previous]
            delta = float((ai-a[previous]+period_rad/2) % period_rad-period_rad/2)
            if dt*max_abs_rate_rad_s >= period_rad/2 or abs(delta)/dt > max_abs_rate_rad_s:
                row['break_reason'] = 'sampling_or_observed_increment_incompatible_with_rate_bound'
                previous = None
        if previous is None:
            groups.append({'start_time_s': float(ti), 'end_time_s': float(ti),
                           'signed_net_turns': 0., 'raw_total_variation_turns': 0.})
            row['phase_rad'] = float(ai)
        else:
            row['signed_delta_rad'] = delta
            row['phase_rad'] = samples[previous]['phase_rad']+delta
            groups[-1]['signed_net_turns'] += delta/(2*math.pi)
            groups[-1]['raw_total_variation_turns'] += abs(delta)/(2*math.pi)
            groups[-1]['end_time_s'] = float(ti)
        row['phase_group'] = len(groups)-1
        samples.append(row)
        previous = i
    complete = bool(np.isfinite(a).all() and len(groups) == 1 and len(t) > 1)
    return {'samples': samples, 'groups': groups,
            'orientation_period_rad': period_rad,
            'assumed_max_abs_rate_rad_s': max_abs_rate_rad_s,
            'complete_under_assumed_sampling_bound': complete,
            'signed_net_turns': groups[0]['signed_net_turns'] if complete else None,
            'raw_total_variation_turns': groups[0]['raw_total_variation_turns'] if complete else None,
            'physical_revolutions': None,
            'scope': 'Direction can reverse. No bridging over missing angles. Raw total variation includes jitter; physical angle and point identity are not validated.'}
