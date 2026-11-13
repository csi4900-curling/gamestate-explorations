"""Replay upstream ByteTrack unchanged and expose association costs for review.

This is a diagnostic, not a replacement tracker. Every replayed frame must
reproduce the saved (track ID, detection index) pairs before interpreting it.
"""
import argparse
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace


def run(reference, output, start, end, track_ids):
    import numpy as np
    import ultralytics
    from ultralytics.engine.results import Boxes
    from ultralytics.trackers.byte_tracker import BYTETracker

    reference, output = Path(reference), Path(output)
    if output.exists():
        raise ValueError('Preserve previous diagnostic')
    if end < start:
        raise ValueError('Invalid diagnostic interval')
    protocol = json.loads((reference/'protocol.json').read_text())
    width, height = protocol['source_size_px']
    selected = set(track_ids)
    trace = []

    class TracedTracker(BYTETracker):
        source_time = None

        def get_dists(self, tracks, detections):
            distances = super().get_dists(tracks, detections)
            if start <= self.source_time <= end:
                for i, track in enumerate(tracks):
                    if track.track_id in selected:
                        trace.append({'time_s': self.source_time,
                                      'stage': 'upstream_get_dists',
                                      'track_id': track.track_id,
                                      'track_state': int(track.state),
                                      'predicted_box': track.xyxy.tolist(),
                                      'last_observation_frame': track.end_frame,
                                      'tracker_frame': self.frame_id,
                                      'detections': [
                                          {'detection_index': int(d.idx),
                                           'box': d.xyxy.tolist(),
                                           'confidence': float(d.score),
                                           'cost': float(distances[i, j])}
                                          for j, d in enumerate(detections)]})
            return distances

    tracker = TracedTracker(SimpleNamespace(**protocol['tracker_config']))
    mismatches = []
    count = 0
    with (reference/'observations.jsonl').open() as stream:
        for line in stream:
            row = json.loads(line)
            tracker.source_time = row['time_s']
            boxes = np.asarray([[*d['bbox_xyxy'], d['confidence'], d['class_id']]
                                for d in row['detections']], dtype=np.float32).reshape(-1, 6)
            tracks = tracker.update(Boxes(boxes, (height, width)))
            actual = sorted((int(t[4]), int(t[-1])) for t in tracks)
            expected = sorted((t['track_id'], t['detection_index'])
                              for t in row['tracked_observations'])
            if actual != expected:
                mismatches.append(row['frame_index'])
            count += 1
            if row['time_s'] > end:
                break
    paths = [reference/'protocol.json', reference/'observations.jsonl',
             Path(__file__), Path(ultralytics.__file__).parent/'trackers/byte_tracker.py']
    def sha(path):
        with path.open('rb') as stream:
            return hashlib.file_digest(stream, 'sha256').hexdigest()
    result = {'development': True, 'diagnostic_only': True,
              'upstream_version': ultralytics.__version__,
              'configuration': protocol['tracker_config'],
              'max_time_lost_samples': tracker.max_frames_lost,
              'review_interval_s': [start, end], 'selected_track_ids': sorted(selected),
              'replayed_frames': count, 'mismatch_frames': mismatches,
              'replay_verified': not mismatches,
              'source_time_step_s': protocol['sample_step_frames']/protocol['source_fps'],
              'hashes': {str(p.resolve()): sha(p) for p in paths},
              'trace': trace,
              'limitations': ['get_dists records first/unconfirmed association costs, not second-stage low-confidence costs.',
                              'Costs and local IDs do not establish physical identity.']}
    output.write_text(json.dumps(result, indent=2)+'\n')
    if mismatches:
        raise ValueError('Replay differs from saved upstream assignments; diagnostic is not accepted')
    return {k: v for k, v in result.items() if k != 'trace'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--start', type=float, required=True)
    parser.add_argument('--end', type=float, required=True)
    parser.add_argument('--track-ids', type=int, nargs='+', required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.reference, args.output, args.start, args.end, args.track_ids), indent=2))
