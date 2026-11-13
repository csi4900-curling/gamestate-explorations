"""Paired development experiment on the existing native registration routine.

Only candidate descriptor correspondence changes: OpenCV reciprocal nearest
matches filter the existing ratio-test pairs. Never invoked by the public run.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time
from unittest.mock import patch

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from vision_core import ViewCalibrator


def reciprocal_pairs(a, b, matcher_factory):
    pairs = matcher_factory().knnMatch(a, b, k=2)
    mutual = matcher_factory(cv2.NORM_L2, crossCheck=True).match(a, b)
    allowed = {(m.queryIdx, m.trainIdx) for m in mutual}
    return [pair for pair in pairs if pair and
            (pair[0].queryIdx, pair[0].trainIdx) in allowed]


def compare(video, times, annotations, calibration, reference_frames, output, modes=('baseline', 'reciprocal_ratio')):
    if not modes or any(m not in ('baseline', 'reciprocal_ratio', 'reciprocal_ratio_usac') for m in modes):
        raise ValueError('Unknown comparison mode')
    output = Path(output)
    if output.exists():
        raise ValueError('Preserve previous comparison outputs')
    output.mkdir(parents=True)
    view = json.loads(Path(annotations).read_text())['views']['left']
    calibrator = ViewCalibrator(view, reference_frames)
    calibrator.H = np.asarray(json.loads(Path(calibration).read_text())['left']['refined_H'])
    original = cv2.BFMatcher
    original_fit = cv2.findHomography
    class ReciprocalMatcher:
        def knnMatch(self, a, b, k):
            if k != 2:
                raise ValueError('Unexpected baseline matcher request')
            return reciprocal_pairs(a, b, original)
    cap = cv2.VideoCapture(str(video))
    fps = cap.get(cv2.CAP_PROP_FPS)
    rows = []
    cv2.setNumThreads(1)
    try:
        for t in times:
            index = round(t*fps)
            cap.set(cv2.CAP_PROP_POS_FRAMES, index)
            ok, frame = cap.read()
            if not ok:
                raise ValueError(f'Missing source frame {index}')
            row = dict(time_s=index/fps, frame_index=index,
                       decoded_pixels_sha256=hashlib.sha256(frame.tobytes()).hexdigest())
            for mode in modes:
                cv2.setRNGSeed(0)
                started = time.perf_counter()
                fits = []
                def capture_fit(a, b, *args, **kwargs):
                    if mode == 'reciprocal_ratio_usac':
                        args = (cv2.USAC_MAGSAC, *args[1:])
                    A, mask = original_fit(a, b, *args, **kwargs)
                    inside = mask.ravel().astype(bool) if mask is not None else np.zeros(len(a), bool)
                    fits.append(dict(matrix=A.tolist() if A is not None else None,
                                     inliers=int(inside.sum()),
                                     unique_target_points=len(np.unique(b[inside], axis=0)),
                                     source_inliers=a[inside].tolist(), target_inliers=b[inside].tolist()))
                    return A, mask
                with patch.object(cv2, 'BFMatcher', original if mode == 'baseline' else ReciprocalMatcher), patch.object(cv2, 'findHomography', capture_fit):
                    H, diagnostic = calibrator.register(frame)
                row[mode] = dict(homography=H.tolist() if H is not None else None,
                                 diagnostic=diagnostic, raw_fits_for_inspection_only=fits,
                                 wall_s=time.perf_counter()-started)
            rows.append(row)
            print(json.dumps({k: row[k]['diagnostic']['status'] for k in modes}), flush=True)
    finally:
        cap.release()
    paths = [Path(__file__), Path(__file__).with_name('vision_core.py'), Path(annotations), Path(calibration), Path(reference_frames)/view['reference_frame']]
    report = dict(development=True, production_modified=False, opencv=cv2.__version__,
                  random_seed=0, threads=1, source=str(Path(video).resolve()),
                  input_hashes={str(p.resolve()): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
                  modes=modes,
                  changed_component='reciprocal_ratio: OpenCV reciprocal matching before unchanged ratio filtering/RANSAC; reciprocal_ratio_usac: additionally substitute OpenCV USAC_MAGSAC, preserving baseline pixel tolerance and iteration budget.',
                  physical_accuracy_verified=False, rows=rows)
    (output/'comparison.json').write_text(json.dumps(report, indent=2))
    return report


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ['video', 'annotations', 'calibration', 'reference-frames', 'output']:
        p.add_argument('--'+name, required=True)
    p.add_argument('--times', type=float, nargs='+', required=True)
    p.add_argument('--modes', nargs='+', default=['baseline', 'reciprocal_ratio'])
    a = p.parse_args()
    compare(a.video, a.times, a.annotations, a.calibration, a.reference_frames, a.output, a.modes)
