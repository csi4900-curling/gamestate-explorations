"""Research probe: handle orientation phase from second moments of stone crops.

The cap is rotationally symmetric, so its contribution to the saturation-weighted
second moments of a size-normalised crop is roughly constant; the elongated
handle adds a term that rotates with the stone. The double angle
atan2(2*Mxy, Mxx-Myy) of that residual advances 2*pi per half turn.

Development probe only. Not wired into the pipeline, not validated, and not a
physical revolution measurement until compared with independent turn counts.
"""
import argparse
import json
from pathlib import Path

import cv2
import numpy as np

SIZE = (64, 40)  # crop width, height after normalisation


def track_boxes(observations, panel, tracker_id):
    rows = []
    with Path(observations).open() as stream:
        for line in stream:
            row = json.loads(line)
            for stone in row['boards'][panel]['stones']:
                if stone.get('tracker_id') == tracker_id and stone['body_point_support']['status'] == 'full_body_box':
                    rows.append((row['frame_index'], *stone['bbox_xyxy']))
    return np.asarray(rows, dtype=float)


def frame_boxes(rows, max_gap_frames):
    """Linear box interpolation for every source frame; observation gaps stay gaps."""
    out = {}
    for a, b in zip(rows[:-1], rows[1:]):
        gap = int(b[0]-a[0])
        if gap > max_gap_frames:
            continue
        for k in range(gap):
            out[int(a[0])+k] = a[1:]+(b[1:]-a[1:])*k/gap
    out[int(rows[-1][0])] = rows[-1][1:]
    return out


def crop_features(frame, box, top_fraction, margin):
    x0, y0, x1, y1 = box
    w, h = x1-x0, y1-y0
    x0, x1 = x0-margin*w, x1+margin*w
    y0, y1 = y0-margin*h, y0+top_fraction*h
    matrix = np.array([[SIZE[0]/(x1-x0), 0, -x0*SIZE[0]/(x1-x0)],
                       [0, SIZE[1]/(y1-y0), -y0*SIZE[1]/(y1-y0)]])
    crop = cv2.warpAffine(frame, matrix, SIZE, flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    weight = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)[:, :, 1].astype(float)/255
    weight = np.clip(weight-np.median(weight), 0, None)
    total = weight.sum()
    if total <= 0:
        return crop, None
    ys, xs = np.mgrid[0:SIZE[1], 0:SIZE[0]]
    # Same pixel scale on both axes, so image angles are not distorted by the crop aspect.
    xs = (xs-SIZE[0]/2)/SIZE[0]; ys = (ys-SIZE[1]/2)/SIZE[0]
    cx, cy = (weight*xs).sum()/total, (weight*ys).sum()/total
    mxx = (weight*(xs-cx)**2).sum()/total
    myy = (weight*(ys-cy)**2).sum()/total
    mxy = (weight*(xs-cx)*(ys-cy)).sum()/total
    return crop, (mxx-myy, 2*mxy, cx, cy, total)


def run(args):
    out = Path(args.output); out.mkdir(parents=True)
    rows = track_boxes(Path(args.job)/'observations/match-observations.jsonl', args.panel, args.tracker)
    boxes = frame_boxes(rows, args.max_gap_frames)
    frames = sorted(f for f in boxes if args.start_frame <= f <= args.end_frame)
    cap = cv2.VideoCapture(args.video)
    fps = cap.get(cv2.CAP_PROP_FPS)
    cap.set(cv2.CAP_PROP_POS_FRAMES, frames[0])
    series = []; tiles = []
    for index in range(frames[0], frames[-1]+1):
        ok, frame = cap.read()
        if not ok:
            break
        if index not in boxes:
            continue
        crop, features = crop_features(frame, boxes[index], args.top_fraction, args.margin)
        if features is not None:
            series.append((index/fps, *features))
        if (index-frames[0]) % args.tile_every == 0:
            tile = cv2.resize(crop, (SIZE[0]*3, SIZE[1]*3), interpolation=cv2.INTER_CUBIC)
            cv2.putText(tile, f'{index/fps:.2f}', (3, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 1)
            tiles.append(tile)
    cap.release()
    series = np.asarray(series)
    t, a, b = series[:, 0], series[:, 1], series[:, 2]
    # Remove the slowly varying cap/scale contribution with a window longer than a half turn.
    window = max(3, int(args.detrend_s*fps) | 1)
    kernel = np.ones(window)/window
    pad = window//2
    smooth = lambda v: np.convolve(np.pad(v, pad, mode='edge'), kernel, mode='valid')
    ra, rb = a-smooth(a), b-smooth(b)
    short = np.ones(args.smooth_frames)/args.smooth_frames
    ra, rb = (np.convolve(np.pad(v, args.smooth_frames//2, mode='edge'), short, mode='valid')[:len(v)] for v in (ra, rb))
    phase = np.unwrap(np.arctan2(rb, ra))
    turns = (phase-phase[0])/(4*np.pi)
    result = {'development': True, 'physical_revolutions': None, 'event': args.event, 'panel': args.panel,
              'tracker_id': args.tracker, 'interval_s': [float(t[0]), float(t[-1])], 'frames': len(t),
              'net_phase_turns': float(turns[-1]), 'total_variation_turns': float(np.abs(np.diff(turns)).sum()),
              'residual_amplitude': [float(np.std(ra)), float(np.std(rb))],
              'settings': {k: getattr(args, k) for k in ['top_fraction', 'margin', 'detrend_s', 'smooth_frames', 'max_gap_frames']},
              'scope': 'Signal probe on development footage; sign and count unverified.'}
    (out/'result.json').write_text(json.dumps(result, indent=2)+'\n')
    np.save(out/'series.npy', np.column_stack([t, a, b, ra, rb, turns]))
    columns = 8
    while len(tiles) % columns:
        tiles.append(np.zeros_like(tiles[0]))
    cv2.imwrite(str(out/'crops.jpg'), np.vstack([np.hstack(tiles[i:i+columns]) for i in range(0, len(tiles), columns)]))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    figure, axes = plt.subplots(3, 1, figsize=(9, 7), sharex=True)
    axes[0].plot(t, a, label='Mxx-Myy'); axes[0].plot(t, b, label='2Mxy'); axes[0].legend(); axes[0].set_ylabel('raw moments')
    axes[1].plot(t, ra, label='residual Mxx-Myy'); axes[1].plot(t, rb, label='residual 2Mxy'); axes[1].legend(); axes[1].axhline(0, color='k', lw=0.5)
    axes[2].plot(t, turns); axes[2].set_ylabel('phase / 4pi (turns)'); axes[2].set_xlabel('source time (s)'); axes[2].grid(True)
    figure.suptitle(f'{args.event} {args.panel} tracker {args.tracker}: development signal probe, not a measurement')
    figure.tight_layout(); figure.savefig(out/'signal.png', dpi=90)
    print(json.dumps(result))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--job', required=True); parser.add_argument('--video', required=True)
    parser.add_argument('--event', required=True); parser.add_argument('--panel', required=True)
    parser.add_argument('--tracker', type=int, required=True); parser.add_argument('--output', required=True)
    parser.add_argument('--start-frame', type=int, default=0); parser.add_argument('--end-frame', type=int, default=10**9)
    parser.add_argument('--top-fraction', type=float, default=0.6); parser.add_argument('--margin', type=float, default=0.1)
    parser.add_argument('--detrend-s', type=float, default=2.0); parser.add_argument('--smooth-frames', type=int, default=5)
    parser.add_argument('--max-gap-frames', type=int, default=6); parser.add_argument('--tile-every', type=int, default=6)
    run(parser.parse_args())
