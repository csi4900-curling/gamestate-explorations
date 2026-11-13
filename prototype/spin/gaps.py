"""Constant-angular-velocity reconstruction of bounded gaps, with explicit ambiguity.

This composes NumPy's phase unwrapping and SciPy linear regression. Thresholds are
assumed development tolerances, not empirically calibrated confidence intervals.
"""
from dataclasses import asdict, dataclass
import math

import numpy as np
from scipy.stats import linregress


@dataclass(frozen=True)
class GapConfig:
    period_rad: float = 2 * math.pi
    fit_window_s: float = 0.5
    min_fit_samples: int = 4
    max_gap_s: float = 2.0
    phase_tolerance_rad: float = 0.15
    rate_tolerance_rad_s: float = 0.2
    max_abs_rate_rad_s: float = 6.0

    def validate(self):
        for key, value in asdict(self).items():
            if not math.isfinite(value) or value <= 0:
                raise ValueError(f'{key} must be positive and finite')
        if self.min_fit_samples < 2 or int(self.min_fit_samples) != self.min_fit_samples:
            raise ValueError('min_fit_samples must be an integer >= 2')


def _runs(mask):
    indices = np.flatnonzero(mask)
    return [r for r in np.split(indices, np.where(np.diff(indices) != 1)[0] + 1) if len(r)]


def _fit(times, phase, ids, side, cfg):
    edge = times[ids[-1] if side == 'left' else ids[0]]
    selected = ids[np.abs(times[ids] - edge) <= cfg.fit_window_s + 1e-9]
    if len(selected) < cfg.min_fit_samples:
        return None
    fitted = linregress(times[selected] - edge, phase[selected])
    residual = phase[selected] - (fitted.intercept + fitted.slope * (times[selected] - edge))
    rmse = float(np.sqrt(np.mean(residual**2)))
    return {'angular_velocity_rad_s': float(fitted.slope),
            'fit_rmse_rad': rmse, 'sample_count': len(selected),
            'sample_indices': selected.tolist(),
            'acceptable': bool(rmse <= cfg.phase_tolerance_rad and abs(fitted.slope) <= cfg.max_abs_rate_rad_s)}


def reconstruct(times, angles, observed, config=None, *, breaks=()):
    """Return observed phases and estimates only inside uniquely reconnectable gaps.

    Angles must already share one stable physical or image coordinate system.
    `breaks` are times of known collisions/cuts: never bridge across one. This
    routine does not detect them. Local phase after an unresolved gap remains local.
    """
    cfg = config or GapConfig()
    cfg.validate()
    t, a, mask = np.asarray(times, float), np.asarray(angles, float), np.asarray(observed, bool)
    if t.ndim != 1 or a.shape != t.shape or mask.shape != t.shape or not len(t):
        raise ValueError('Times, angles, observed must be nonempty matching vectors')
    if not np.isfinite(t).all() or np.any(np.diff(t) <= 0):
        raise ValueError('Times must be finite and strictly increasing')
    if not np.isfinite(a[mask]).all():
        raise ValueError('Observed angles must be finite')
    if not np.isfinite(list(breaks)).all():
        raise ValueError('Breaks must be finite')
    # A cut/collision also splits continuously visible runs; no cross-boundary unwrap.
    runs = []
    for r in _runs(mask):
        cut = [i for i in range(1, len(r)) if any(t[r[i-1]] < b <= t[r[i]] for b in breaks)]
        runs.extend(np.split(r, cut))
    phase = np.full(len(t), np.nan)
    for r in runs:
        phase[r] = np.unwrap(a[r], period=cfg.period_rad)
    rows = [{'time_s': float(ti), 'observed_angle_rad': float(ai) if oi else None,
             'phase_rad': None, 'status': 'observed' if oi else 'unresolved',
             'phase_group': None} for ti, ai, oi in zip(t, a, mask)]
    gaps, fit_rows = [], []
    group = 0
    for run_index, r in enumerate(runs):
        if run_index:
            prev = runs[run_index - 1]
            left, right = int(prev[-1]), int(r[0])
            duration = float(t[right] - t[left])
            gap = {'left_index': left, 'right_index': right, 'duration_s': duration,
                   'status': 'unresolved', 'candidate_turn_offsets': []}
            lf, rf = _fit(t, phase, prev, 'left', cfg), _fit(t, phase, r, 'right', cfg)
            gap.update(left_fit=lf, right_fit=rf)
            if any(t[left] < b <= t[right] for b in breaks):
                gap['reason'] = 'known_collision_or_camera_break'
            elif duration > cfg.max_gap_s:
                gap['reason'] = 'gap_exceeds_development_limit'
            elif lf is None or rf is None:
                gap['reason'] = 'insufficient_visible_window'
            elif not lf['acceptable'] or not rf['acceptable']:
                gap['reason'] = 'visible_window_not_constant_rate'
            elif any(np.any(np.diff(t[rr]) * cfg.max_abs_rate_rad_s >= cfg.period_rad / 2) for rr in [prev, r]):
                gap['reason'] = 'sampling_can_alias_rotation'
            elif abs(lf['angular_velocity_rad_s'] - rf['angular_velocity_rad_s']) > cfg.rate_tolerance_rad_s:
                gap['reason'] = 'angular_velocity_changed_across_gap'
            else:
                w0, w1 = lf['angular_velocity_rad_s'], rf['angular_velocity_rad_s']
                # Both endpoint rates constrain the constant speed in the gap.
                tolerance = cfg.rate_tolerance_rad_s + 2 * cfg.phase_tolerance_rad / duration
                lo = max(w0 - tolerance, w1 - tolerance, -cfg.max_abs_rate_rad_s)
                hi = min(w0 + tolerance, w1 + tolerance, cfg.max_abs_rate_rad_s)
                d = phase[right] - phase[left]
                first = math.ceil((lo * duration - d) / cfg.period_rad - 1e-10)
                last = math.floor((hi * duration - d) / cfg.period_rad + 1e-10)
                candidates = list(range(first, last + 1))
                gap['candidate_turn_offsets'] = candidates
                if len(candidates) == 1:
                    offset = candidates[0] * cfg.period_rad
                    phase[r] += offset
                    ids = np.arange(left + 1, right)
                    phase[ids] = np.interp(t[ids], [t[left], t[right]], [phase[left], phase[right]])
                    gap.update(status='estimated', reason='unique_reconnection_under_assumed_tolerances',
                               angular_velocity_rad_s=float((phase[right] - phase[left]) / duration),
                               signed_turns=float((phase[right] - phase[left]) / (2 * math.pi)))
                    for i in ids:
                        rows[i].update(status='estimated', phase_rad=float(phase[i]), phase_group=group)
                else:
                    gap['reason'] = 'ambiguous_turn_count' if candidates else 'endpoint_incompatible_with_constant_rate'
            if gap['status'] != 'estimated':
                group += 1
            gaps.append(gap)
        for i in r:
            rows[i].update(phase_rad=float(phase[i]), phase_group=group)
        fit_rows.append({'start_index': int(r[0]), 'end_index': int(r[-1]),
                         'phase_group': group, 'left_window': _fit(t, phase, r, 'right', cfg),
                         'right_window': _fit(t, phase, r, 'left', cfg)})
    complete = bool(mask[0] and mask[-1] and all(g['status'] == 'estimated' for g in gaps))
    # Sparse observations may alias even without a missing frame.
    unaliased = all(not np.any(np.diff(t[r]) * cfg.max_abs_rate_rad_s >= cfg.period_rad / 2) for r in runs)
    total = float((phase[-1] - phase[0]) / (2 * math.pi)) if complete and unaliased else None
    return {'model': 'constant_angular_velocity_per_gap_v1', 'config': asdict(cfg),
            'tolerances_are': 'assumed development bounds, not calibrated confidence',
            'samples': rows, 'gaps': gaps, 'visible_runs': fit_rows,
            'signed_turns_over_input_interval': total,
            'observed_count': int(mask.sum()),
            'estimated_count': sum(r['status'] == 'estimated' for r in rows),
            'unresolved_count': sum(r['status'] == 'unresolved' for r in rows),
            'sampling_unaliased_under_configured_max_rate': unaliased}


def evaluate_hidden_intervals(times, angles, observed, intervals, config=None, *, breaks=()):
    """Hide measured angles BEFORE fitting; evaluate only otherwise observed samples.

    Caller supplies provenance. Model-produced angles yield a consistency check,
    not independent physical accuracy. Each interval is evaluated independently.
    """
    t, a, visible = np.asarray(times, float), np.asarray(angles, float), np.asarray(observed, bool)
    cfg = config or GapConfig()
    results = []
    for start, end in intervals:
        hidden = (t >= start) & (t <= end)
        withheld = hidden & visible
        fit_visible = visible & ~hidden
        rec = reconstruct(t, a, fit_visible, cfg, breaks=breaks)
        ids = [i for i in np.flatnonzero(withheld) if rec['samples'][i]['status'] == 'estimated']
        errors = []
        for i in ids:
            delta = rec['samples'][i]['phase_rad'] - a[i]
            errors.append((delta + cfg.period_rad / 2) % cfg.period_rad - cfg.period_rad / 2)
        # Whole-turn error needs an uninterrupted reference spanning the gap.
        turn_errors = []
        for gap in rec['gaps']:
            l, r = gap['left_index'], gap['right_index']
            if gap['status'] != 'estimated' or not np.any(withheld[l:r+1]) or not np.all(visible[l:r+1]):
                continue
            if np.any(np.diff(t[l:r+1]) * cfg.max_abs_rate_rad_s >= cfg.period_rad / 2):
                continue
            reference = np.unwrap(a[l:r+1], period=cfg.period_rad)
            turn_errors.append(float(gap['signed_turns'] - (reference[-1] - reference[0]) / (2 * math.pi)))
        results.append({'interval_s': [start, end], 'withheld_observed_samples': int(withheld.sum()),
                        'estimated_withheld_samples': len(ids),
                        'wrapped_angle_mae_deg': float(np.degrees(np.mean(np.abs(errors)))) if errors else None,
                        'wrapped_angle_max_error_deg': float(np.degrees(np.max(np.abs(errors)))) if errors else None,
                        'signed_turn_count_errors': turn_errors,
                        'gaps': rec['gaps']})
    return results


def main():
    """Analyze timestamped angle observations without requiring a video tracker."""
    import argparse
    import json
    from pathlib import Path
    from .point_tracking import digest
    parser = argparse.ArgumentParser(description='Constant-rate gap reconstruction from supplied angular observations')
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Output exists; preserve previous results')
    data = json.loads(args.input.read_text())
    if not data.get('provenance') or not data.get('coordinate_system'):
        parser.error('Input needs provenance and coordinate_system')
    rows = data['samples']
    times = [r['time_s'] for r in rows]
    angles = [r['angle_rad'] if r.get('angle_rad') is not None else float('nan') for r in rows]
    visible = [r.get('angle_rad') is not None for r in rows]
    config = GapConfig(**data.get('config', {}))
    result = reconstruct(times, angles, visible, config, breaks=data.get('known_breaks_s', []))
    result.update(input_sha256=digest(args.input), provenance=data['provenance'],
                  coordinate_system=data['coordinate_system'],
                  interpretation='Conditional reconstruction from supplied angles; accuracy inherits observation provenance',
                  masked_evaluation=evaluate_hidden_intervals(times, angles, visible, data.get('evaluation_masks_s', []),
                                                             config, breaks=data.get('known_breaks_s', [])))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    print(args.output)


if __name__ == '__main__':
    main()
