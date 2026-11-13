"""Research probe: spin rate and sense from the handle's colour-centroid cycle.

The handle is asymmetric (gooseneck at one end), so the saturation-weighted
centroid of a registered, size-normalised stone crop moves around a small
ellipse once per full turn. A constant-rate harmonic model is fitted to both
centroid coordinates over a grid of rates; the quadrature between the two
coordinates gives the sense of the on-screen loop.

Development probe on inspected footage. The rate is an image measurement over
the stated interval only; it is not a validated physical revolution count, and
the mapping from on-screen loop sense to in-turn/out-turn is unverified.
"""
import argparse
import json
from pathlib import Path

import cv2
import numpy as np

from handle_phase import SIZE, frame_boxes, track_boxes

SETTINGS = {'margin': 0.1, 'top_fraction': 0.6, 'box_degree': 4, 'register_passes': 2, 'register_reach_px': 6,
            'minimum_box_width_px': 24, 'minimum_frames': 60, 'rate_grid_hz': [0.05, 1.5, 0.005],
            'provenance': 'Engineering defaults chosen on one development throw; not validated.'}


def registered_crops(video, boxes, first, last):
    frames = sorted(f for f in boxes if first <= f <= last)
    if len(frames) < 8:
        return np.empty(0), np.empty(0)
    index = np.asarray(frames, dtype=float); centre = index.mean()
    values = np.asarray([boxes[f] for f in frames])
    degree = min(SETTINGS['box_degree'], len(frames)-1)
    fitted = np.column_stack([np.polyval(np.polyfit(index-centre, values[:, k], degree), index-centre) for k in range(4)])
    smooth = dict(zip(frames, fitted))
    cap = cv2.VideoCapture(str(video)); fps = cap.get(cv2.CAP_PROP_FPS)
    cap.set(cv2.CAP_PROP_POS_FRAMES, frames[0])
    times, images = [], []
    for f in range(frames[0], frames[-1]+1):
        ok, frame = cap.read()
        if not ok:
            break
        if f not in smooth:
            continue
        x0, y0, x1, y1 = smooth[f]; w, h = x1-x0, y1-y0
        x0, x1 = x0-SETTINGS['margin']*w, x1+SETTINGS['margin']*w
        y0, y1 = y0-SETTINGS['margin']*h, y0+SETTINGS['top_fraction']*h
        m = np.array([[SIZE[0]/(x1-x0), 0, -x0*SIZE[0]/(x1-x0)], [0, SIZE[1]/(y1-y0), -y0*SIZE[1]/(y1-y0)]])
        images.append(cv2.warpAffine(frame, m, SIZE, flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE))
        times.append(f/fps)
    cap.release()
    images = np.asarray(images); reach = SETTINGS['register_reach_px']
    band = slice(int(SIZE[1]*0.55), SIZE[1])
    # Frame judder and box noise: register on the rotation-invariant cap rim and granite band.
    for _ in range(SETTINGS['register_passes']):
        gray = np.asarray([cv2.cvtColor(i, cv2.COLOR_BGR2GRAY) for i in images], dtype=np.float32)
        template = np.median(gray, axis=0)[band, reach:SIZE[0]-reach]
        for k in range(len(images)):
            search = cv2.copyMakeBorder(gray[k], reach, reach, 0, 0, cv2.BORDER_REPLICATE)[band.start:band.stop+2*reach]
            _, _, _, (bx, by) = cv2.minMaxLoc(cv2.matchTemplate(search, template, cv2.TM_CCOEFF_NORMED))
            if (bx, by) != (reach, reach):
                images[k] = cv2.warpAffine(images[k], np.float32([[1, 0, reach-bx], [0, 1, reach-by]]), SIZE,
                                           borderMode=cv2.BORDER_REPLICATE)
    return np.asarray(times), images


def centroids(images):
    ys, xs = np.mgrid[0:SIZE[1], 0:SIZE[0]]
    rows = []
    for image in images:
        weight = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)[:, :, 1].astype(float)/255
        weight = np.clip(weight-np.median(weight), 0, None)
        total = weight.sum()
        rows.append([(weight*xs).sum()/total, (weight*ys).sum()/total] if total > 0 else [np.nan, np.nan])
    return np.asarray(rows)


def harmonic_fit(t, xy):
    """Constant-rate fit of offset + drift + one sinusoid to both coordinates."""
    good = np.isfinite(xy).all(1); t, xy = t[good], xy[good]
    tau = t-t.mean()
    low, high, step = SETTINGS['rate_grid_hz']
    low = max(low, 0.75/(t[-1]-t[0]))  # at least three quarters of a cycle inside the interval
    base = np.column_stack([np.ones(len(t)), tau])
    residual_base = xy-base@np.linalg.lstsq(base, xy, rcond=None)[0]
    best = None; curve = []
    for rate in np.arange(low, high, step):
        design = np.column_stack([base, np.cos(2*np.pi*rate*tau), np.sin(2*np.pi*rate*tau)])
        coefficients = np.linalg.lstsq(design, xy, rcond=None)[0]
        residual = xy-design@coefficients
        gain = 1-(residual**2).sum()/(residual_base**2).sum()
        curve.append((float(rate), float(gain)))
        if best is None or gain > best[1]:
            best = (float(rate), float(gain), coefficients, residual)
    rate, gain, c, residual = best
    # x = Ax cos + Bx sin, y = Ay cos + By sin: the loop is traversed with the sign of Ax*By - Bx*Ay.
    sense = float(np.sign(c[2, 0]*c[3, 1]-c[3, 0]*c[2, 1]))
    amplitude = [float(np.hypot(c[2, k], c[3, k])) for k in range(2)]
    half = max(v for _, v in curve)-(max(v for _, v in curve)-np.median([v for _, v in curve]))/2
    support = [r for r, v in curve if v >= half]
    return {'rate_hz': rate, 'explained_fraction': gain, 'amplitude_crop_px': amplitude,
            'residual_crop_px': float(np.sqrt((residual**2).mean())),
            'screen_loop_sense': 'clockwise' if sense > 0 else 'counterclockwise',
            'rate_half_gain_interval_hz': [min(support), max(support)], 'frames_used': int(len(t)),
            'interval_s': [float(t[0]), float(t[-1])], 'turns_in_interval': rate*float(t[-1]-t[0])}


def ellipse_phase(t, xy):
    """Unwrapped angle of the centroid around a drifting, axis-aligned ellipse.

    Unlike a rate fit, the angle is local, so a second harmonic or fewer than two
    cycles cannot move the answer to a multiple of the rate. A soft loss keeps
    occluded or mis-cropped frames from steering the centre.
    """
    from scipy.optimize import least_squares
    good = np.isfinite(xy).all(1); t, xy = t[good], xy[good]
    tau = (t-t.mean())/max(t[-1]-t[0], 1e-6)
    centre = np.median(xy, 0); spread = 1.4826*np.median(np.abs(xy-centre), 0)+1e-3

    def normalised(q):
        return (xy[:, 0]-q[0]-q[2]*tau)/np.exp(q[4]), (xy[:, 1]-q[1]-q[3]*tau)/np.exp(q[5])

    def residual(q):
        u, v = normalised(q)
        return np.hypot(u, v)-1

    fit = least_squares(residual, [centre[0], centre[1], 0, 0, *np.log(np.clip(1.5*spread, 0.35, 2.9))],
                        loss='soft_l1', f_scale=0.3,
                        # A short noisy arc otherwise fits an arbitrarily large, distant ellipse. The handle
                        # offset is a small fraction of the 64-pixel crop, so centre, drift and axes are bounded.
                        bounds=([centre[0]-2, centre[1]-2, -3, -3, np.log(0.3), np.log(0.3)],
                                [centre[0]+2, centre[1]+2, 3, 3, np.log(3.0), np.log(3.0)]))
    u, v = normalised(fit.x)
    radius = np.hypot(u, v); inlier = np.abs(radius-1) < 0.6
    if inlier.sum() < 10:
        return {'status': 'unavailable', 'reason': 'centroid_path_is_not_a_loop'}
    angle = np.unwrap(np.arctan2(v[inlier], u[inlier])); ti = t[inlier]
    width = 7; smooth = np.convolve(np.pad(angle, width//2, mode='edge'), np.ones(width)/width, mode='valid')
    turns = (smooth[-1]-smooth[0])/(2*np.pi); travelled = np.abs(np.diff(smooth)).sum()/(2*np.pi)
    return {'status': 'image_phase_estimate', 'turns_in_interval': float(abs(turns)),
            'screen_loop_sense': 'clockwise' if turns > 0 else 'counterclockwise',
            'rate_hz': float(abs(turns)/(ti[-1]-ti[0])), 'interval_s': [float(ti[0]), float(ti[-1])],
            'frames_used': int(inlier.sum()), 'inlier_fraction': float(inlier.mean()),
            'monotonic_fraction': float(abs(turns)/travelled) if travelled else 0.0,
            'ellipse_axes_crop_px': [float(np.exp(fit.x[4])), float(np.exp(fit.x[5]))],
            'radius_scatter': float(np.std(radius[inlier])),
            '_path': np.column_stack([ti, u[inlier], v[inlier], smooth/(2*np.pi)])}


def estimate(job, video, panel, tracker, start_s, end_s):
    rows = track_boxes(Path(job)/'observations/match-observations.jsonl', panel, tracker)
    if not len(rows):
        return {'status': 'unavailable', 'reason': 'no_full_body_track_observations'}
    rows = rows[(rows[:, 3]-rows[:, 1]) >= SETTINGS['minimum_box_width_px']]
    boxes = frame_boxes(rows, 6) if len(rows) > 1 else {}
    t, images = registered_crops(video, boxes, round(start_s*30), round(end_s*30))
    if len(t) < SETTINGS['minimum_frames']:
        return {'status': 'unavailable', 'reason': 'too_few_frames', 'frames': int(len(t))}
    xy = centroids(images)
    result = ellipse_phase(t, xy)
    result['harmonic_rate_fit'] = harmonic_fit(t, xy)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--job', required=True); parser.add_argument('--video', required=True)
    parser.add_argument('--throws', required=True, help='throw-effects effects.json for receiving intervals')
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    events = json.loads((Path(args.job)/'observations/events.json').read_text())['events']
    effects = {e['event_id']: e for e in json.loads(Path(args.throws).read_text())['events']}
    results = []; paths = {}
    for event in events:
        row = {'event_id': event['id'], 'physical_revolutions': None}
        # Sending view: from shortly before the line crossing (after release) to the end of the track.
        row['sending'] = estimate(args.job, args.video, 'left', event['track_id'],
                                  event['crossing_time_s']-1.2, event['crossing_time_s']+10)
        effect = effects.get(event['id'], {})
        if effect.get('status') == 'review_proposal':
            row['receiving'] = estimate(args.job, args.video, effect['panel'], effect['delivered_tracker_id'],
                                        effect['arrival_time_s'], effect['settle_interval_s'][0])
        else:
            row['receiving'] = {'status': 'unavailable', 'reason': 'no_receiving_track_for_event'}
        for view in ('sending', 'receiving'):
            path = row[view].pop('_path', None)
            if path is not None:
                paths[(event['id'], view)] = path
        results.append(row)
        print(event['id'], {k: (round(v.get('turns_in_interval', 0), 2), round(v.get('rate_hz', 0), 3), v.get('screen_loop_sense'),
                                round(v.get('monotonic_fraction', 0), 2), round(v.get('inlier_fraction', 0), 2),
                                [round(x, 2) for x in v.get('ellipse_axes_crop_px', [])], v.get('reason'))
                            for k, v in row.items() if isinstance(v, dict)}, flush=True)
    Path(args.output).write_text(json.dumps({'development': True, 'settings': SETTINGS, 'events': results,
                                             'scope': 'Image phase probe on inspected development footage; not validated.'}, indent=2)+'\n')
    import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
    figure, axes = plt.subplots(4, len(events), figsize=(2.2*len(events), 8))
    for column, event in enumerate(events):
        for block, view in enumerate(('sending', 'receiving')):
            path = paths.get((event['id'], view))
            top, bottom = axes[2*block, column], axes[2*block+1, column]
            top.set_title(f"{event['id']} {view}", fontsize=7); top.set_xticks([]); top.set_yticks([])
            bottom.tick_params(labelsize=6)
            if path is None:
                continue
            top.scatter(path[:, 1], path[:, 2], c=path[:, 0], s=3, cmap='viridis'); top.set_aspect('equal'); top.invert_yaxis()
            bottom.plot(path[:, 0], path[:, 3]-path[0, 3]); bottom.grid(True)
    figure.suptitle('Centroid loop (normalised, colour = time) and unwrapped turns: development probe, not a measurement')
    figure.tight_layout(); figure.savefig(Path(args.output).with_suffix('.png'), dpi=80)
