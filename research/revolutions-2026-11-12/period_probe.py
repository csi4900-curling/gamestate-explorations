"""Research probe: full-turn period from the self-similarity of registered stone crops.

Uses every pixel of the handle region instead of a one-pixel centroid shift. The
mean correlation between crops separated by a lag peaks when the handle returns
to the same pose; mirrored half-turn poses correlate less. Constant rate is
assumed only inside the analysed interval. Development probe, not a measurement.
"""
import json, sys
from pathlib import Path
import cv2
import numpy as np
import spin_estimate as S
from handle_phase import SIZE, frame_boxes, track_boxes


FULL_TURN_MINIMUM = 0.3  # engineering default from ten development throws; not validated


def lag_curve(t, images, min_overlap_s=1.2):
    gray = np.asarray([cv2.cvtColor(i, cv2.COLOR_BGR2GRAY) for i in images], dtype=float)[:, :int(SIZE[1]*0.7)]
    x = gray.reshape(len(t), -1)
    x = (x-x.mean(1, keepdims=True))/x.std(1, keepdims=True)
    design = np.column_stack([np.ones(len(t)), t-t.mean()])
    x = x-design@np.linalg.lstsq(design, x, rcond=None)[0]
    x /= np.linalg.norm(x, axis=1, keepdims=True)
    similarity = x@x.T
    step = np.median(np.diff(t)); curve = []
    for lag in range(1, len(t)):
        if (len(t)-lag)*step < min_overlap_s:
            break
        curve.append((lag*step, float(np.mean(np.diag(similarity, lag)))))
    return np.asarray(curve)


def period(curve, shortest_s=1.0, allow_half_turn=True):
    lags, values = curve[:, 0], curve[:, 1]
    smooth = np.convolve(np.pad(values, 2, mode='edge'), np.ones(5)/5, mode='valid')
    peaks = [i for i in range(1, len(lags)-1) if lags[i] >= shortest_s and smooth[i] > smooth[i-1] and smooth[i] >= smooth[i+1]]
    if not peaks:
        return None
    best = max(peaks, key=lambda i: smooth[i])
    half = int(np.argmin(np.abs(lags-lags[best]/2)))
    # A full-turn return correlates strongly; the mirrored half-turn pose only weakly. When the
    # interval is too short to reach the full-turn peak, the strongest peak is the weak half-turn
    # bump and the curve is still rising at the longest lag.
    if allow_half_turn and smooth[best] < FULL_TURN_MINIMUM and smooth[-1] >= 2*smooth[best]:
        return {'period_s': float(2*lags[best]), 'rate_hz': float(0.5/lags[best]), 'basis': 'twice_half_turn_peak',
                'similarity_at_period': None, 'similarity_at_half_period': float(smooth[best]), 'other_peaks': []}
    if smooth[best] < FULL_TURN_MINIMUM:
        return {'period_s': None, 'rate_hz': None, 'basis': 'no_clear_full_turn_peak',
                'similarity_at_period': float(smooth[best]), 'similarity_at_half_period': float(smooth[half]),
                'other_peaks': [(round(float(lags[i]), 2), round(float(smooth[i]), 3)) for i in peaks][:6]}
    return {'period_s': float(lags[best]), 'rate_hz': float(1/lags[best]), 'similarity_at_period': float(smooth[best]),
            'basis': 'full_turn_peak', 'similarity_at_half_period': float(smooth[half]),
            'other_peaks': [(round(float(lags[i]), 2), round(float(smooth[i]), 3)) for i in peaks if i != best][:4]}


def analyse(job, video, panel, tracker, start_s, end_s, allow_half_turn=True):
    rows = track_boxes(Path(job)/'observations/match-observations.jsonl', panel, tracker)
    rows = rows[(rows[:, 3]-rows[:, 1]) >= S.SETTINGS['minimum_box_width_px']] if len(rows) else rows
    if len(rows) < 2:
        return {'status': 'unavailable'}, None
    t, images = S.registered_crops(video, frame_boxes(rows, 6), round(start_s*30), round(end_s*30))
    if len(t) < 75:
        return {'status': 'unavailable', 'frames': int(len(t))}, None
    curve = lag_curve(t, images)
    found = period(curve, allow_half_turn=allow_half_turn)
    return ({'status': 'image_period_estimate', 'interval_s': [float(t[0]), float(t[-1])], **found}
            if found else {'status': 'no_peak', 'interval_s': [float(t[0]), float(t[-1])]}), curve


if __name__ == '__main__':
    job, video, throws, output = sys.argv[1:5]
    events = json.loads((Path(job)/'observations/events.json').read_text())['events']
    effects = {e['event_id']: e for e in json.loads(Path(throws).read_text())['events']}
    import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
    figure, axes = plt.subplots(2, len(events), figsize=(2.2*len(events), 4.2), sharey=True)
    results = []
    for column, event in enumerate(events):
        row = {'event_id': event['id'], 'physical_revolutions': None}
        effect = effects.get(event['id'], {})
        windows = {'sending': ('left', event['track_id'], event['crossing_time_s']-1.2, event['crossing_time_s']+10)}
        if effect.get('status') == 'review_proposal':
            windows['receiving'] = (effect['panel'], effect['delivered_tracker_id'], effect['arrival_time_s'], effect['settle_interval_s'][0]-0.5)
        for index, view in enumerate(('sending', 'receiving')):
            axes[index, column].set_title(f"{event['id']} {view}", fontsize=7); axes[index, column].tick_params(labelsize=6)
            if view not in windows:
                row[view] = {'status': 'unavailable'}; continue
            # The receiving view's weak, multi-peaked curves do not support the half-turn inference.
            row[view], curve = analyse(job, video, *windows[view], allow_half_turn=view == 'sending')
            if curve is not None:
                axes[index, column].plot(curve[:, 0], curve[:, 1]); axes[index, column].grid(True)
                if row[view].get('period_s'): axes[index, column].axvline(row[view]['period_s'], color='r', lw=0.8)
        results.append(row)
        print(event['id'], {v: (row[v].get('period_s') and round(row[v]['period_s'], 2), row[v].get('basis')) for v in ('sending', 'receiving')}, flush=True)
    figure.suptitle('Mean crop similarity versus lag (s); red = chosen period. Development probe, not a measurement'); figure.tight_layout()
    figure.savefig(Path(output).with_suffix('.png'), dpi=80)
    Path(output).write_text(json.dumps({'development': True, 'events': results, 'scope': 'Image period probe on inspected development footage; not validated.'}, indent=2)+'\n')
