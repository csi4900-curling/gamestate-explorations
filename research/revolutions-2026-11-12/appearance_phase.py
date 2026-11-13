"""Research probe: rotation phase from the appearance cycle of size-normalised stone crops.

A rotating handle seen from a nearly fixed direction traces a closed loop in
image space. After removing each pixel's linear trend, the two leading principal
components of the crop sequence are plotted and their joint phase unwrapped.
Whether one loop is a half turn or a full turn depends on handle asymmetry and
is NOT decided here. Development probe only; no physical revolution claim.
"""
import argparse, json
from pathlib import Path
import cv2
import numpy as np
from handle_phase import SIZE, frame_boxes, track_boxes


def crops(args):
    rows = track_boxes(Path(args.job)/'observations/match-observations.jsonl', args.panel, args.tracker)
    boxes = frame_boxes(rows, 6)
    # Detector boxes jitter by about a pixel at 10 Hz, which dominates the appearance of a
    # 40-pixel stone. The stone moves smoothly, so fit each box coordinate over the interval.
    inside = sorted(f for f in boxes if args.start_s*30-1 <= f <= args.end_s*30+1)
    if args.box_degree >= 0:
        frames = np.asarray(inside, dtype=float); centre = frames.mean()
        values = np.asarray([boxes[f] for f in inside])
        fitted = np.column_stack([np.polyval(np.polyfit(frames-centre, values[:, k], args.box_degree), frames-centre) for k in range(4)])
        boxes = {f: fitted[i] for i, f in enumerate(inside)}
    cap = cv2.VideoCapture(args.video); fps = cap.get(cv2.CAP_PROP_FPS)
    first, last = round(args.start_s*fps), round(args.end_s*fps)
    cap.set(cv2.CAP_PROP_POS_FRAMES, first)
    times, images = [], []
    for index in range(first, last+1):
        ok, frame = cap.read()
        if not ok: break
        if index not in boxes: continue
        x0, y0, x1, y1 = boxes[index]; w, h = x1-x0, y1-y0
        x0, x1, y0, y1 = x0-args.margin*w, x1+args.margin*w, y0-args.margin*h, y0+args.top_fraction*h
        m = np.array([[SIZE[0]/(x1-x0), 0, -x0*SIZE[0]/(x1-x0)], [0, SIZE[1]/(y1-y0), -y0*SIZE[1]/(y1-y0)]])
        images.append(cv2.warpAffine(frame, m, SIZE, flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE))
        times.append(index/fps)
    cap.release()
    return np.asarray(times), np.asarray(images)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('job', 'video', 'event', 'panel', 'output'): p.add_argument('--'+name, required=True)
    p.add_argument('--tracker', type=int, required=True)
    p.add_argument('--start-s', type=float, required=True); p.add_argument('--end-s', type=float, required=True)
    p.add_argument('--register-passes', type=int, default=2)
    p.add_argument('--box-degree', type=int, default=4)
    p.add_argument('--top-fraction', type=float, default=0.6); p.add_argument('--margin', type=float, default=0.1)
    args = p.parse_args()
    out = Path(args.output); out.mkdir(parents=True)
    t, images = crops(args)
    # The 30 fps stream carries a 5 Hz judder (repeated frames from a slower source), so the
    # stone shifts against any smooth box. Register every crop on its rotation-invariant lower
    # band (cap rim and granite shoulders) against the temporal median.
    shifts = np.zeros((len(t), 2))
    for _ in range(args.register_passes):
        gray = np.asarray([cv2.cvtColor(i, cv2.COLOR_BGR2GRAY) for i in images], dtype=np.float32)
        band = slice(int(SIZE[1]*0.55), SIZE[1]); reach = 6
        template = np.median(gray, axis=0)[band, reach:SIZE[0]-reach]
        for k in range(len(t)):
            search = cv2.copyMakeBorder(gray[k], reach, reach, 0, 0, cv2.BORDER_REPLICATE)[band.start:band.stop+2*reach]
            score = cv2.matchTemplate(search, template, cv2.TM_CCOEFF_NORMED)
            _, _, _, (bx, by) = cv2.minMaxLoc(score)
            dx, dy = reach-bx, reach-by
            if dx or dy:
                images[k] = cv2.warpAffine(images[k], np.float32([[1, 0, dx], [0, 1, dy]]), SIZE, borderMode=cv2.BORDER_REPLICATE)
                shifts[k] += (dx, dy)
    gray = np.asarray([cv2.cvtColor(i, cv2.COLOR_BGR2GRAY) for i in images], dtype=float)
    x = gray.reshape(len(t), -1)
    x = (x-x.mean(1, keepdims=True))/x.std(1, keepdims=True)
    # Remove each pixel's mean and linear drift (scale/viewpoint change along the sheet).
    design = np.column_stack([np.ones(len(t)), t-t.mean()])
    x = x-design@np.linalg.lstsq(design, x, rcond=None)[0]
    u, s, _ = np.linalg.svd(x, full_matrices=False)
    pcs = u[:, :4]*s[:4]
    smooth = lambda v: np.convolve(np.pad(v, 2, mode='edge'), np.ones(5)/5, mode='valid')
    a, b = smooth(pcs[:, 0]), smooth(pcs[:, 1])
    loops = (np.unwrap(np.arctan2(b, a))-np.arctan2(b[0], a[0]))/(2*np.pi)
    # Dominant frequency of each component, for comparison with the phase estimate.
    dt = np.median(np.diff(t)); freqs = np.fft.rfftfreq(4096, dt)
    peak = [float(freqs[1:][np.argmax(np.abs(np.fft.rfft(pcs[:, k]*np.hanning(len(t)), 4096))[1:])]) for k in range(4)]
    similarity = np.corrcoef(x)
    result = {'development': True, 'physical_revolutions': None, 'event': args.event, 'panel': args.panel,
              'tracker_id': args.tracker, 'interval_s': [float(t[0]), float(t[-1])], 'frames': len(t),
              'registration_shift_px_std': [float(v) for v in shifts.std(0)],
              'explained_variance': [float(v) for v in (s[:4]**2/np.sum(s**2))],
              'component_peak_hz': peak, 'appearance_loops_net': float(loops[-1]),
              'appearance_loops_total_variation': float(np.abs(np.diff(loops)).sum()),
              'loop_meaning': 'One loop is a half or a full turn; undetermined by this probe.'}
    (out/'result.json').write_text(json.dumps(result, indent=2)+'\n')
    np.savez_compressed(out/'series.npz', t=t, pcs=pcs, loops=loops, images=images)
    import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
    f, ax = plt.subplots(2, 2, figsize=(11, 7))
    for k in range(3): ax[0, 0].plot(t, pcs[:, k], label=f'PC{k+1} ({result["explained_variance"][k]:.0%}, {peak[k]:.2f} Hz)')
    ax[0, 0].legend(fontsize=8); ax[0, 0].set_xlabel('source time (s)')
    ax[0, 1].plot(a, b, lw=0.8); ax[0, 1].scatter(a[0], b[0], c='g'); ax[0, 1].set_title('PC1 vs PC2 (green = start)')
    ax[1, 0].plot(t, loops); ax[1, 0].grid(True); ax[1, 0].set_ylabel('appearance loops'); ax[1, 0].set_xlabel('source time (s)')
    ax[1, 1].imshow(similarity, extent=[t[0], t[-1], t[-1], t[0]], cmap='viridis'); ax[1, 1].set_title('crop self-similarity')
    f.suptitle(f'{args.event} {args.panel}: appearance-cycle probe (development, not a measurement)'); f.tight_layout(); f.savefig(out/'signal.png', dpi=85)
    print(json.dumps(result))

main()
