"""Exact-input replay of saved match observations, with geometry/OCR state restore.

Development adapter. The public frozen pipeline does not import this module.
No detector identities, homographies or scores are changed by replay.
"""
import copy
import hashlib
import json
from pathlib import Path
import time


class MatchObservationReplay:
    def __init__(self, observer, cache, current_protocol):
        self.observer = observer
        self.cache = Path(cache)
        previous = json.loads((self.cache/'protocol.json').read_text())
        for key in ['source_sha256', 'source_fps', 'source_size_px', 'sample_step_frames', 'opencv_build_sha256']:
            if previous[key] != current_protocol[key]:
                raise ValueError(f'Match cache input differs: {key}')
        if previous['source_interval_s'][0] != current_protocol['source_interval_s'][0]:
            raise ValueError('Match replay requires the same initial time to restore state')
        saved = json.loads((self.cache/'match-observation-protocol.json').read_text())
        for key in ['config_sha256', 'code_sha256', 'ocr_versions', 'ocr_model_sha256']:
            if saved[key] != observer.provenance[key]:
                raise ValueError(f'Match cache implementation differs: {key}')
        if sorted(saved['reference_sha256'].values()) != sorted(observer.provenance['reference_sha256'].values()):
            raise ValueError('Match cache reference content differs')
        if observer.config['geometry_mode'] != 'original_split_geometry_with_anchor_reuse':
            raise ValueError('Geometry state restoration not implemented for this mode')
        self.paths = [self.cache/'match-observations.jsonl', self.cache/'observations.jsonl']
        self.stats = [(p.stat().st_size, p.stat().st_mtime_ns) for p in self.paths]
        self.streams = [p.open() for p in self.paths]
        self.pending = self._next()
        self.reused = 0
        self.replay_s = 0.
        self.provenance = {'cache': str(self.cache.resolve()),
                           'input_sha256': {str(p): self._sha(p) for p in self.paths},
                           'policy': 'Exact prediction rows; saved output unchanged; restore saved automatic anchor and OCR chronology; no tracker state restored.'}

    @staticmethod
    def _sha(path):
        with path.open('rb') as f:
            return hashlib.file_digest(f, 'sha256').hexdigest()

    def _next(self):
        board = self.streams[0].readline()
        if not board:
            return None
        detections = self.streams[1].readline()
        if not detections:
            raise ValueError('Cached board has no corresponding detection row')
        a, b = json.loads(board), json.loads(detections)
        if (a['frame_index'], a['time_s']) != (b['frame_index'], b['time_s']):
            raise ValueError('Cached observation streams are misaligned')
        return a, b

    def _restore(self, frame, saved):
        import cv2
        import numpy as np
        from prototype.camera_geometry import features
        from prototype.body_localization import transported_reference_camera
        o = self.observer
        board = saved['boards']['right']
        H = board.get('homography_normalized_pixels_to_local_metres')
        if H is not None:
            anchor_time = board['registration']['anchor_time_s']
            if 'right' not in o.geometry.anchors:
                if anchor_time != saved['time_s']:
                    raise ValueError('Missing cached anchor initialization frame')
                normalized = cv2.resize(frame, (640, 360))
                H = np.asarray(H, dtype=float)
                o.geometry.anchors['right'] = dict(
                    time_s=anchor_time, frame=normalized.copy(), H=H,
                    features=features(normalized, (320, 0, 640, 360)),
                    prior=transported_reference_camera(H, H, (320, 0, 640, 360)),
                    initialization=copy.deepcopy(board['registration']))
            elif o.geometry.anchors['right']['time_s'] != anchor_time:
                raise ValueError('Unexpected cached geometry anchor change')
        score = saved.get('score_observation')
        if score is not None:
            o.next_score = saved['time_s'] + o.interval
            o.score_stream.write(json.dumps(score)+'\n')
            o.score_stream.flush()
        o.last_score = {team: {k: v for k, v in reading.items() if k != 'age_s'}
                        for team, reading in saved['last_observed_totals'].items()}

    def observe(self, frame, row):
        for p, expected in zip(self.paths, self.stats):
            if (p.stat().st_size, p.stat().st_mtime_ns) != expected:
                raise ValueError('Match cache changed during replay')
        if self.pending is None:
            return self.observer.observe(frame, row)
        started = time.perf_counter()
        saved, detections = self.pending
        for key in ['frame_index', 'time_s', 'detections', 'tracked_observations']:
            if row[key] != detections[key]:
                raise ValueError(f'Match cache prediction differs: {key}')
        self._restore(frame, saved)
        self.observer.stream.write(json.dumps(saved)+'\n')
        self.observer.stream.flush()
        self.observer.count += 1
        self.reused += 1
        self.pending = self._next()
        self.replay_s += time.perf_counter()-started
        return saved

    def close(self):
        for stream in self.streams:
            stream.close()
        summary = self.observer.close()
        summary['observation_replay'] = {**self.provenance, 'samples': self.reused,
                                         'wall_seconds': self.replay_s,
                                         'recorded_OCR_row_runtime_belongs_to_original_run': True}
        (self.observer.output/'match-observation-summary.json').write_text(json.dumps(summary, indent=2))
        return summary
