"""Honest per-throw revolution-rate estimation from registered stone crops.

Builds on the development self-similarity period probe (research/revolutions-2026-11-12):
registers 30 fps stone crops on the rotation-invariant granite/rim band to remove
broadcast frame judder, measures the full-turn appearance lag peak, evaluates
quadrature loop sense at that fixed period, and saves a visual filmstrip for human
inspection. Observed interval metrics and constant-rate whole-throw extrapolations
are kept strictly separate; physical_revolutions stays null until independently validated.
"""
import argparse
import json
import math
import time
from pathlib import Path

import cv2
import numpy as np

from prototype.detection_cache import digest

SIZE = (64, 40)
FULL_TURN_MINIMUM = 0.30
SENSE_MIN_EXPLAINED = 0.20

SETTINGS = {
    'margin': 0.1,
    'top_fraction': 0.6,
    'box_degree': 4,
    'register_passes': 2,
    'register_reach_px': 6,
    'minimum_box_width_px': 24,
    'minimum_frames': 75,
    'min_overlap_s': 1.2,
    'shortest_period_s': 1.0,
    'full_turn_minimum': FULL_TURN_MINIMUM,
    'sense_min_explained': SENSE_MIN_EXPLAINED,
    'filmstrip_frames': 12,
    'provenance': 'Development self-similarity period estimator; not independently validated physical spin.',
}


def frame_boxes(rows, max_gap_frames):
    """Linear box interpolation across source frames; larger gaps stay uninterpolated."""
    if len(rows) == 0:
        return {}
    out = {}
    for a, b in zip(rows[:-1], rows[1:]):
        gap = int(b[0] - a[0])
        if gap <= 0 or gap > max_gap_frames:
            continue
        for k in range(gap):
            out[int(a[0]) + k] = a[1:] + (b[1:] - a[1:]) * (k / gap)
    out[int(rows[-1][0])] = rows[-1][1:]
    return out


def registered_crops(cap, fps, boxes, first, last, settings=SETTINGS):
    frames = sorted(f for f in boxes if first <= f <= last)
    if len(frames) < 8:
        return np.empty(0), np.empty(0)
    index = np.asarray(frames, dtype=float)
    centre = index.mean()
    values = np.asarray([boxes[f] for f in frames], dtype=float)
    degree = min(settings['box_degree'], len(frames) - 1)
    fitted = np.column_stack(
        [np.polyval(np.polyfit(index - centre, values[:, k], degree), index - centre) for k in range(4)]
    )
    smooth = dict(zip(frames, fitted))
    cap.set(cv2.CAP_PROP_POS_FRAMES, frames[0])
    times, images = [], []
    for f in range(frames[0], frames[-1] + 1):
        ok, frame = cap.read()
        if not ok:
            break
        if f not in smooth:
            continue
        x0, y0, x1, y1 = smooth[f]
        w, h = x1 - x0, y1 - y0
        if w <= 1 or h <= 1:
            continue
        x0, x1 = x0 - settings['margin'] * w, x1 + settings['margin'] * w
        y0, y1 = y0 - settings['margin'] * h, y0 + settings['top_fraction'] * h
        m = np.array([[SIZE[0] / (x1 - x0), 0, -x0 * SIZE[0] / (x1 - x0)],
                      [0, SIZE[1] / (y1 - y0), -y0 * SIZE[1] / (y1 - y0)]])
        images.append(cv2.warpAffine(frame, m, SIZE, flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE))
        times.append(f / fps)
    if len(images) < 8:
        return np.empty(0), np.empty(0)
    images = np.asarray(images)
    reach = settings['register_reach_px']
    band = slice(int(SIZE[1] * 0.55), SIZE[1])
    for _ in range(settings['register_passes']):
        gray = np.asarray([cv2.cvtColor(i, cv2.COLOR_BGR2GRAY) for i in images], dtype=np.float32)
        template = np.median(gray, axis=0)[band, reach:SIZE[0] - reach]
        for k in range(len(images)):
            search = cv2.copyMakeBorder(gray[k], reach, reach, 0, 0, cv2.BORDER_REPLICATE)[
                band.start:band.stop + 2 * reach
            ]
            _, _, _, (bx, by) = cv2.minMaxLoc(cv2.matchTemplate(search, template, cv2.TM_CCOEFF_NORMED))
            if (bx, by) != (reach, reach):
                images[k] = cv2.warpAffine(
                    images[k],
                    np.float32([[1, 0, reach - bx], [0, 1, reach - by]]),
                    SIZE,
                    borderMode=cv2.BORDER_REPLICATE,
                )
    return np.asarray(times), images


def lag_curve(t, images, min_overlap_s=1.2):
    gray = np.asarray([cv2.cvtColor(i, cv2.COLOR_BGR2GRAY) for i in images], dtype=float)[:, :int(SIZE[1] * 0.7)]
    x = gray.reshape(len(t), -1)
    std = x.std(1, keepdims=True)
    if np.any(std < 1e-8):
        std = np.maximum(std, 1e-8)
    x = (x - x.mean(1, keepdims=True)) / std
    design = np.column_stack([np.ones(len(t)), t - t.mean()])
    x = x - design @ np.linalg.lstsq(design, x, rcond=None)[0]
    norms = np.linalg.norm(x, axis=1, keepdims=True)
    x = x / np.maximum(norms, 1e-8)
    similarity = x @ x.T
    step = float(np.median(np.diff(t)))
    curve = []
    for lag in range(1, len(t)):
        if (len(t) - lag) * step < min_overlap_s:
            break
        curve.append((lag * step, float(np.mean(np.diag(similarity, lag)))))
    return np.asarray(curve) if curve else np.empty((0, 2))


def estimate_period(curve, shortest_s=1.0, full_turn_minimum=FULL_TURN_MINIMUM, allow_half_turn=True):
    if len(curve) < 5:
        return None
    lags, values = curve[:, 0], curve[:, 1]
    smooth = np.convolve(np.pad(values, 2, mode='edge'), np.ones(5) / 5.0, mode='valid')
    peaks = [i for i in range(1, len(lags) - 1)
             if lags[i] >= shortest_s and smooth[i] > smooth[i - 1] and smooth[i] >= smooth[i + 1]]
    if not peaks:
        return None
    best = max(peaks, key=lambda i: smooth[i])
    half = int(np.argmin(np.abs(lags - lags[best] / 2.0)))
    if allow_half_turn and smooth[best] < full_turn_minimum and smooth[-1] >= 2.0 * smooth[best]:
        return {
            'period_s': float(2.0 * lags[best]),
            'rate_hz': float(0.5 / lags[best]),
            'basis': 'twice_half_turn_peak',
            'similarity_at_period': None,
            'similarity_at_half_period': float(smooth[best]),
        }
    if smooth[best] < full_turn_minimum:
        return {
            'period_s': None,
            'rate_hz': None,
            'basis': 'no_clear_full_turn_peak',
            'similarity_at_period': float(smooth[best]),
            'similarity_at_half_period': float(smooth[half]),
        }
    return {
        'period_s': float(lags[best]),
        'rate_hz': float(1.0 / lags[best]),
        'basis': 'full_turn_peak',
        'similarity_at_period': float(smooth[best]),
        'similarity_at_half_period': float(smooth[half]),
    }


def fixed_rate_loop_sense(t, images, rate_hz, min_explained=SENSE_MIN_EXPLAINED):
    """Evaluate 2D handle-centroid quadrature strictly at the fixed lag-curve frequency."""
    if rate_hz is None or rate_hz <= 0 or len(t) < 12:
        return {'screen_loop_sense': None, 'explained_fraction': None, 'status': 'unavailable'}
    ys, xs = np.mgrid[0:int(SIZE[1] * 0.7), 0:SIZE[0]]
    pts = []
    for image in images:
        top = image[:int(SIZE[1] * 0.7)]
        sat = cv2.cvtColor(top, cv2.COLOR_BGR2HSV)[:, :, 1].astype(float) / 255.0
        w = np.clip(sat - np.median(sat), 0.0, None)
        tot = float(w.sum())
        pts.append([float((w * xs).sum() / tot), float((w * ys).sum() / tot)] if tot > 0 else [np.nan, np.nan])
    xy = np.asarray(pts, dtype=float)
    good = np.isfinite(xy).all(1)
    if good.sum() < 12:
        return {'screen_loop_sense': None, 'explained_fraction': None, 'status': 'unavailable'}
    tg, xyg = t[good], xy[good]
    tau = tg - tg.mean()
    base = np.column_stack([np.ones(len(tg)), tau])
    res_base = xyg - base @ np.linalg.lstsq(base, xyg, rcond=None)[0]
    denom = float((res_base ** 2).sum())
    if denom <= 1e-12:
        return {'screen_loop_sense': None, 'explained_fraction': None, 'status': 'ambiguous'}
    design = np.column_stack([base, np.cos(2 * np.pi * rate_hz * tau), np.sin(2 * np.pi * rate_hz * tau)])
    coef = np.linalg.lstsq(design, xyg, rcond=None)[0]
    res = xyg - design @ coef
    explained = float(1.0 - (res ** 2).sum() / denom)
    cross = float(coef[2, 0] * coef[3, 1] - coef[3, 0] * coef[2, 1])
    if explained < min_explained or abs(cross) < 1e-6:
        return {
            'screen_loop_sense': None,
            'explained_fraction': round(explained, 3),
            'status': 'ambiguous',
        }
    return {
        'screen_loop_sense': 'clockwise' if cross > 0 else 'counterclockwise',
        'explained_fraction': round(explained, 3),
        'status': 'screen_loop_quadrature_unverified',
    }


def save_filmstrip(t, images, out_path, count=12):
    if len(images) == 0:
        return None
    n = min(count, len(images))
    indices = np.linspace(0, len(images) - 1, n).round().astype(int)
    scale = 2
    tw, th = SIZE[0] * scale, SIZE[1] * scale
    label_h = 18
    canvas = np.full((th + label_h, n * tw, 3), 24, dtype=np.uint8)
    t0 = float(t[indices[0]])
    for col, idx in enumerate(indices):
        tile = cv2.resize(images[idx], (tw, th), interpolation=cv2.INTER_CUBIC)
        canvas[:th, col * tw:(col + 1) * tw] = tile
        cv2.putText(
            canvas, f'+{t[idx] - t0:.1f}s', (col * tw + 6, th + 13),
            cv2.FONT_HERSHEY_SIMPLEX, 0.42, (230, 235, 240), 1, cv2.LINE_AA,
        )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out_path), canvas)
    return out_path.name


def analyse_view(cap, fps, rows, start_s, end_s, max_gap_frames, *, allow_half_turn=True, filmstrip_path=None, settings=SETTINGS):
    if len(rows) == 0:
        return {'status': 'unavailable', 'reason': 'no_full_body_boxes'}
    arr = np.asarray(rows, dtype=float)
    arr = arr[(arr[:, 3] - arr[:, 1]) >= settings['minimum_box_width_px']]
    if len(arr) < 2:
        return {'status': 'unavailable', 'reason': 'stone_crop_too_small'}
    boxes = frame_boxes(arr, max_gap_frames)
    t, images = registered_crops(cap, fps, boxes, round(start_s * fps), round(end_s * fps), settings=settings)
    if len(t) < settings['minimum_frames']:
        return {'status': 'unavailable', 'reason': 'insufficient_frames', 'frames': int(len(t))}
    curve = lag_curve(t, images, min_overlap_s=settings['min_overlap_s'])
    found = estimate_period(
        curve,
        shortest_s=settings['shortest_period_s'],
        full_turn_minimum=settings['full_turn_minimum'],
        allow_half_turn=allow_half_turn,
    )
    duration_s = float(t[-1] - t[0])
    strip_name = save_filmstrip(t, images, filmstrip_path, count=settings['filmstrip_frames']) if filmstrip_path else None
    if not found or found.get('period_s') is None:
        return {
            'status': 'no_clear_peak',
            'interval_s': [float(t[0]), float(t[-1])],
            'duration_s': round(duration_s, 3),
            'frames': int(len(t)),
            'filmstrip': strip_name,
            **(found or {}),
        }
    rate_hz = found['rate_hz']
    sense = fixed_rate_loop_sense(t, images, rate_hz, min_explained=settings['sense_min_explained'])
    return {
        'status': 'observed_period_estimate',
        'interval_s': [float(t[0]), float(t[-1])],
        'duration_s': round(duration_s, 3),
        'frames': int(len(t)),
        'observed_turns_in_interval': round(duration_s * rate_hz, 2),
        'filmstrip': strip_name,
        **found,
        'sense': sense,
    }


def run(*, public_run, aggregate, effects, video, output, settings=None):
    public_run, output = Path(public_run), Path(output)
    settings = {**SETTINGS, **(settings or {})}
    started = time.perf_counter()
    protocol = json.loads((public_run / 'protocol.json').read_text())
    agg = json.loads(Path(aggregate).read_text())
    eff_by_id = {e['event_id']: e for e in json.loads(Path(effects).read_text())['events']}
    fps = float(protocol.get('source_fps') or 30.0)
    sample_step = int(protocol.get('sample_step_frames') or 3)
    max_gap_frames = max(6, 2 * sample_step)

    # Identify the exact departure and receiving (panel, tracker_id) pairs needed.
    needed = set()
    specs = []
    for event in agg['events']:
        eid = event['candidate_id']
        eff = eff_by_id.get(eid, {})
        dep_segs = [s for s in event.get('segments', []) if s.get('role') == 'departure' and s.get('pixel_points')]
        rec_segs = [s for s in event.get('segments', []) if s.get('role') == 'receiving' and s.get('pixel_points')]
        dep_info = None
        if len(dep_segs) == 1:
            s = dep_segs[0]
            panel = s.get('rink_panel') or {'left_split': 'left', 'right_split': 'right'}[s['camera']]
            pts = s['pixel_points']
            s0, s1 = max(0.0, pts[0]['time_s']), pts[-1]['time_s']
            hog_ev = s.get('hog_crossing_evidence') or {}
            primary_c = event['event_prediction']['crossing_time_s']
            if hog_ev.get('crossing_time_s') is not None:
                dep_cross = float(hog_ev['crossing_time_s'])
            elif s0 - 1.0 <= primary_c <= s1 + 1.0:
                dep_cross = float(primary_c)
            else:
                dep_cross = max(s0, s1 - 5.0)
            dep_info = (panel, s['tracker_id'], s0, s1, dep_cross)
            needed.add((panel, s['tracker_id']))
        rec_info = None
        if eff.get('status') == 'review_proposal' and eff.get('settle_interval_s'):
            panel, tid = eff['panel'], eff['delivered_tracker_id']
            rec_info = (panel, tid, eff['arrival_time_s'], max(eff['arrival_time_s'], eff['settle_interval_s'][0] - 0.5))
            needed.add((panel, tid))
        elif len(rec_segs) == 1:
            s = rec_segs[0]
            panel = s.get('rink_panel') or {'left_split': 'left', 'right_split': 'right'}[s['camera']]
            pts = s['pixel_points']
            rec_info = (panel, s['tracker_id'], pts[0]['time_s'], pts[-1]['time_s'])
            needed.add((panel, s['tracker_id']))
        specs.append((eid, event, eff, dep_info, rec_info))

    # Single streaming pass over match-observations.jsonl to gather all needed boxes.
    track_rows = {key: [] for key in needed}
    if needed:
        with (public_run / 'match-observations.jsonl').open() as stream:
            for line in stream:
                row = json.loads(line)
                fi = row['frame_index']
                for panel, board in row['boards'].items():
                    for stone in board['stones']:
                        key = (panel, stone.get('tracker_id'))
                        if key in track_rows and stone['body_point_support']['status'] == 'full_body_box':
                            track_rows[key].append((fi, *stone['bbox_xyxy']))

    spin_dir = output.parent / 'spin'
    cap = cv2.VideoCapture(str(video))
    results = []
    try:
        for eid, event, eff, dep_info, rec_info in specs:
            entry = {
                'event_id': eid,
                'crossing_time_s': event['event_prediction']['crossing_time_s'],
                'physical_revolutions': None,
                'sending': {'status': 'unavailable'},
                'receiving': {'status': 'unavailable'},
                'modeled_whole_throw_estimate': None,
            }
            if dep_info is not None:
                panel, tid, s0, s1, dep_cross = dep_info
                # Trim sending window to free-sliding travel near/after hog release
                # (rules require release before the hog line; earlier frames have the
                # delivery stick holding the handle stationary and occluding spin).
                win_start = max(s0, dep_cross - 0.5)
                win_end = min(s1, dep_cross + 10.0)
                entry['sending'] = analyse_view(
                    cap, fps, track_rows.get((panel, tid), []), win_start, win_end, max_gap_frames,
                    allow_half_turn=True, filmstrip_path=spin_dir / f'{eid}-sending.png', settings=settings,
                )
                entry['sending']['panel'] = panel
                entry['sending']['tracker_id'] = tid
            if rec_info is not None:
                panel, tid, r0, r1 = rec_info
                entry['receiving'] = analyse_view(
                    cap, fps, track_rows.get((panel, tid), []), r0, r1, max_gap_frames,
                    allow_half_turn=False, filmstrip_path=None, settings=settings,
                )
                entry['receiving']['panel'] = panel
                entry['receiving']['tracker_id'] = tid
            # Separate constant-rate extrapolation over travel time (never reported as observed).
            rate = entry['sending'].get('rate_hz')
            if rate is not None and eff.get('status') == 'review_proposal' and eff.get('settle_interval_s'):
                send_iv = entry['sending'].get('interval_s')
                start_t = float(send_iv[0]) if send_iv else (dep_info[4] if dep_info is not None else event['event_prediction']['crossing_time_s'])
                stop_t = float(eff['settle_interval_s'][0])
                travel_s = max(0.0, stop_t - start_t)
                if travel_s > 0:
                    entry['modeled_whole_throw_estimate'] = {
                        'estimated_turns': round(rate * travel_s, 2),
                        'assumed_rate_hz': round(rate, 4),
                        'travel_interval_s': [round(start_t, 2), round(stop_t, 2)],
                        'travel_duration_s': round(travel_s, 2),
                        'status': 'modeled_constant_rate_extrapolation_unverified',
                        'note': 'Constant-rate extrapolation from observed sending-view interval over travel time; not an observed whole-throw count.',
                    }
            results.append(entry)
    finally:
        cap.release()

    with_sending = sum(1 for r in results if r['sending'].get('period_s') is not None)
    with_receiving = sum(1 for r in results if r['receiving'].get('period_s') is not None)
    with_sense = sum(1 for r in results if (r['sending'].get('sense') or {}).get('screen_loop_sense') is not None)
    payload = {
        'schema_version': 'curling-throw-revolutions-development-v1',
        'development': True,
        'source_sha256': protocol['source_sha256'],
        'events': results,
        'summary': {
            'candidates': len(results),
            'sending_period_estimates': with_sending,
            'receiving_period_estimates': with_receiving,
            'sending_sense_estimates': with_sense,
            'physical_revolutions_validated': False,
            'wall_seconds': round(time.perf_counter() - started, 2),
        },
        'provenance': {
            'settings': settings,
            'code_sha256': digest(__file__),
            'limitations': [
                'Image self-similarity period over the visible interval only; not validated physical revolution ground truth.',
                'Modeled whole-throw estimates assume constant angular rate and are separated from observed turns.',
                'Screen-loop sense has not been independently validated against physical CW/CCW spin labels.',
            ],
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, allow_nan=False) + '\n')
    return payload


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('public-run', 'aggregate', 'effects', 'video', 'output'):
        parser.add_argument('--' + name, required=True)
    print(json.dumps(run(**vars(parser.parse_args()))['summary']))
