"""Development-only comparison: propagate SIFT features with upstream OpenCV LK.

The original ViewCalibrator matcher, homography fit and acceptance rules remain
unchanged. No production integration, new thresholds, fallback or frame skipping.
Descriptors identify the initial features; they are NOT recomputed on later frames.
Each supplied clip starts with fresh SIFT. Optical-flow failures remain missing.
"""
import argparse
import hashlib
import json
from pathlib import Path
import time

import cv2
import numpy as np

from prototype.vision_core import ViewCalibrator
from prototype.painted_landmark_evaluation import evaluate


class PropagatedFeatures:
    def __init__(self, extractor):
        self.extractor = extractor
        self.previous = None
        self.points = None
        self.descriptors = None
        self.initializations = 0
        self.flow_calls = 0

    def detectAndCompute(self, gray, mask):
        if self.previous is None:
            keypoints, descriptors = self.extractor.detectAndCompute(gray, mask)
            self.points = np.array([k.pt for k in keypoints], np.float32).reshape(-1, 1, 2)
            self.descriptors = descriptors
            self.initializations += 1
        elif self.points is not None and len(self.points):
            points, status, _ = cv2.calcOpticalFlowPyrLK(self.previous, gray, self.points, None)
            self.flow_calls += 1
            if points is None or status is None:
                self.points = np.empty((0, 1, 2), np.float32)
                self.descriptors = None
            else:
                keep = status.ravel().astype(bool) & np.isfinite(points).all(axis=(1, 2))
                xy = points[:, 0]
                h, w = gray.shape
                keep &= (xy[:, 0] >= 0) & (xy[:, 0] < w) & (xy[:, 1] >= 0) & (xy[:, 1] < h)
                if mask is not None:
                    indices = np.flatnonzero(keep)
                    pixels = xy[indices].astype(int)
                    keep[indices] &= mask[pixels[:, 1], pixels[:, 0]] != 0
                self.points = points[keep]
                self.descriptors = self.descriptors[keep] if keep.any() else None
        self.previous = gray.copy()
        return [cv2.KeyPoint(float(p[0]), float(p[1]), 1.) for p in self.points[:, 0]], self.descriptors


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()


def compare(plan_path, output):
    plan_path, output = Path(plan_path), Path(output)
    plan = json.loads(plan_path.read_text())
    if output.exists():
        raise ValueError('Preserve previous comparison')
    output.mkdir(parents=True)
    cv2.setNumThreads(plan['opencv_threads'])
    view = json.loads(Path(plan['annotations']).read_text())['views']['left']
    calibrated = np.asarray(json.loads(Path(plan['calibration']).read_text())['left']['refined_H'])
    provenance = {'development': True, 'plan': plan, 'plan_sha256': sha(plan_path),
                  'input_sha256': {key: sha(plan[key]) for key in ['video', 'annotations', 'calibration', 'references']},
                  'code_sha256': {name: sha(Path(__file__).with_name(name)) for name in ['temporal_feature_comparison.py', 'vision_core.py', 'painted_landmark_evaluation.py']},
                  'opencv_version': cv2.__version__, 'opencv_threads': cv2.getNumThreads(),
                  'production_enabled': False, 'new_application_thresholds': False,
                  'flow_parameters': 'OpenCV calcOpticalFlowPyrLK defaults',
                  'limitation': 'Initial descriptors are retained while points move; correspondence can drift or move with people. No automatic reseeding or fallback.'}
    (output/'protocol.json').write_text(json.dumps(provenance, indent=2)+'\n')
    cap = cv2.VideoCapture(plan['video'])
    fps = cap.get(cv2.CAP_PROP_FPS)
    records = []
    try:
        for ci, clip in enumerate(plan['clips']):
            models = {name: ViewCalibrator(view, plan['reference_frames']) for name in ['baseline', 'flow']}
            for model in models.values(): model.H = calibrated.copy()
            wrapper = PropagatedFeatures(models['flow'].sift)
            models['flow'].sift = wrapper
            for si, index in enumerate(clip['frame_indices']):
                cap.set(cv2.CAP_PROP_POS_FRAMES, index)
                ok, frame = cap.read()
                if not ok or round(cap.get(cv2.CAP_PROP_POS_FRAMES))-1 != index:
                    raise ValueError('Exact source frame unavailable')
                frame = cv2.resize(frame, (1920, 1080))
                row = {'clip': ci, 'frame_index': index, 'time_s': index/fps}
                for name in (['baseline', 'flow'] if si % 2 == 0 else ['flow', 'baseline']):
                    cv2.setRNGSeed(0)
                    clock = time.perf_counter()
                    H, diag = models[name].register(frame)
                    row[name] = {'wall_seconds': time.perf_counter()-clock, 'diagnostic': diag,
                                 'H': (H @ np.diag([3., 3., 1.])).tolist() if H is not None else None}
                records.append(row)
                with (output/'rows.jsonl').open('a') as stream: stream.write(json.dumps(row)+'\n')
            (output/f'clip-{ci:02d}.json').write_text(json.dumps({'initial_sift_calls': wrapper.initializations, 'flow_calls': wrapper.flow_calls})+'\n')
    finally:
        cap.release()
    references = json.loads(Path(plan['references']).read_text())
    reference_frames = {x['frame_index'] for x in references['frames']}
    result = {'runtime': {}, 'landmarks': {}}
    for name in ['baseline', 'flow']:
        result['runtime'][name] = {'wall_seconds': sum(r[name]['wall_seconds'] for r in records),
                                   'accepted': sum(r[name]['H'] is not None for r in records), 'samples': len(records)}
        rows = [{'frame_index': r['frame_index'], 'boards': {'left': {'homography_normalized_pixels_to_local_metres': r[name]['H']}, 'right': {}}} for r in records if r['frame_index'] in reference_frames]
        result['landmarks'][name] = evaluate(references, rows)
    (output/'result.json').write_text(json.dumps(result, indent=2)+'\n')
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--plan', required=True)
    p.add_argument('--output', required=True)
    a = p.parse_args()
    print(json.dumps(compare(a.plan, a.output)['runtime']))
