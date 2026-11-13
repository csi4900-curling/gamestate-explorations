"""Compare maintained upstream trackers on immutable saved detections.

Development component experiment. No labels enter association; no pipeline
replacement, cross-view identity claim, or physical accuracy score is produced.
"""
import argparse
import hashlib
import json
from pathlib import Path
import time
from types import SimpleNamespace
from itertools import zip_longest


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def compare_assignments(reference_rows, candidate_rows, reference_track_ids):
    """Compare local labels on exactly shared detections, without spatial matching."""
    selected = set(reference_track_ids)
    observations = []
    for reference, candidate in zip_longest(reference_rows, candidate_rows):
        if reference is None or candidate is None:
            raise ValueError('Tracker output lengths differ')
        if (reference['frame_index'], reference['time_s'], reference['detections']) != (
                candidate['frame_index'], candidate['time_s'], candidate['detections']):
            raise ValueError('Tracker inputs differ; detection indices cannot be compared')
        for track in reference['tracked_observations']:
            if track['track_id'] not in selected:
                continue
            ids = [other['track_id'] for other in candidate['tracked_observations']
                   if other['detection_index'] == track['detection_index']]
            observations.append({'time_s': reference['time_s'],
                                 'frame_index': reference['frame_index'],
                                 'reference_track_id': track['track_id'],
                                 'detection_index': track['detection_index'],
                                 'candidate_ids_on_same_detection': ids})
    summary = {}
    for identity in sorted(selected):
        rows = [row for row in observations if row['reference_track_id'] == identity]
        summary[str(identity)] = {
            'reference_observations': len(rows),
            'unique_candidate_ids': sorted({i for r in rows for i in r['candidate_ids_on_same_detection']}),
            'missing_candidate_observations': sum(not r['candidate_ids_on_same_detection'] for r in rows),
            'multiple_candidate_observations': sum(len(r['candidate_ids_on_same_detection']) > 1 for r in rows)}
    return {'physical_identity_accuracy': None,
            'scope': 'Local labels on identical detections; reference tracker is not physical identity ground truth',
            'summary': summary, 'observations': observations}


def comparison_coverage(events, protocol, rows, *, allow_partial=False, progress=None):
    from prototype.public_event_audit import verify_scan
    if events['status'] == 'development_complete_event_stage':
        return verify_scan(events, rows)
    if not allow_partial or events['status'] != 'partial_development_snapshot_not_completed_match':
        raise ValueError('Partial snapshots require explicit opt-in')
    if not progress or progress['events_so_far'] != events['events']:
        raise ValueError('Snapshot events differ from committed progress')
    if progress['samples'] != events['sampled_frames'] or not rows:
        raise ValueError('Snapshot sample count differs from progress')
    if rows[-1]['time_s'] != progress['source_time_s']:
        raise ValueError('Snapshot boundary differs from progress')
    if events['source_sha256'] != protocol['source_sha256']:
        raise ValueError('Snapshot source differs from protocol')
    # Reuse frame-integrity verification for the declared prefix only. The
    # original event status is preserved on disk and in the comparison plan.
    coverage = verify_scan({**events, 'status': 'development_complete_event_stage'}, rows)
    return {**coverage, 'complete_requested_scan': False, 'complete_declared_prefix': True,
            'partial_run': True, 'requested_full_interval_s': protocol['source_interval_s']}


def run(reference, video, output, *, allow_partial=False, candidate='botsort',reid_checkpoint=None):
    import cv2
    import numpy as np
    import ultralytics
    from ultralytics.engine.results import Boxes
    from ultralytics.trackers.byte_tracker import BYTETracker
    from ultralytics.trackers.bot_sort import BOTSORT
    from ultralytics.trackers.oc_sort import OCSORT
    from ultralytics.utils import YAML

    reference, video, output = map(Path, (reference, video, output))
    if output.exists():
        raise ValueError('Preserve previous comparison')
    events = json.loads((reference/'events.json').read_text())
    protocol = json.loads((reference/'protocol.json').read_text())
    if digest(video) != events['source_sha256']:
        raise ValueError('Source video mismatch')
    rows = [json.loads(line) for line in (reference/'observations.jsonl').open()]
    progress_path = reference/'progress.json'
    coverage = comparison_coverage(events, protocol, rows, allow_partial=allow_partial,
                                  progress=json.loads(progress_path.read_text()) if allow_partial else None)
    upstream = Path(ultralytics.__file__).parent
    candidates = {'botsort': BOTSORT, 'botsort-reid':BOTSORT, 'ocsort': OCSORT}
    if candidate not in candidates:
        raise ValueError('Unsupported comparison candidate')
    candidate_config = upstream/('cfg/trackers/'+('botsort' if candidate=='botsort-reid' else candidate)+'.yaml')
    settings = {'bytetrack': protocol['tracker_config'], candidate: YAML.load(candidate_config)}
    if candidate=='botsort-reid':
        if reid_checkpoint is None or not Path(reid_checkpoint).is_file():
            raise ValueError('Appearance comparison requires an explicit local checkpoint')
        settings[candidate].update(with_reid=True,model=str(Path(reid_checkpoint).resolve()),device='cpu')
        import torch
        torch.set_num_threads(4)
    elif reid_checkpoint is not None:raise ValueError('ReID checkpoint requires botsort-reid')
    output.mkdir(parents=True)
    plan = {'development': True, 'source_sha256': events['source_sha256'],
            'coverage': coverage, 'configurations': settings,
            'ultralytics': ultralytics.__version__,
            'opencv_build_sha256': hashlib.sha256(cv2.getBuildInformation().encode()).hexdigest(),
            'opencv_threads': cv2.getNumThreads(),
            'reid_enabled': candidate=='botsort-reid',
            'reid_checkpoint_sha256':digest(Path(reid_checkpoint)) if reid_checkpoint else None,
            'reid_device':'cpu' if reid_checkpoint else None,
            'reid_torch_threads':4 if reid_checkpoint else None,
            'candidate': candidate,
            'hypothesis': 'Compare default upstream association on identical detections before considering any replacement.',
            'acceptance': 'First reproduce saved ByteTrack assignments exactly; then review candidate identity continuity on the same source evidence. Track count is not identity accuracy.',
            'limitations': ['BoT-SORT default GMC uses the full split-screen image; a single camera motion model may not fit both panels.',
                           'Same development excerpt previously inspected; not an independent generalization test.',
                           'Concurrent workloads; timing is not isolated throughput.'],
            'inputs': {str(p.resolve()): digest(p) for p in [reference/'observations.jsonl', reference/'events.json', reference/'protocol.json', candidate_config, Path(__file__), upstream/'trackers/byte_tracker.py', upstream/'trackers/bot_sort.py', upstream/'trackers/oc_sort.py', upstream/'trackers/utils/gmc.py']}}
    (output/'plan.json').write_text(json.dumps(plan, indent=2))
    if reid_checkpoint:
        for path in [Path(reid_checkpoint),upstream/'trackers/utils/reid.py']:
            plan['inputs'][str(path.resolve())]=digest(path)
        plan['limitations'].append('Generic upstream classification embeddings are not trained for curling-stone identity; test source-reviewed errors before adoption.')
        (output/'plan.json').write_text(json.dumps(plan,indent=2))
    (output/'tracker_component_comparison.py').write_bytes(Path(__file__).read_bytes())
    results = {}
    for name, cls in [('bytetrack', BYTETracker), (candidate, candidates[candidate])]:
        tracker = cls(SimpleNamespace(**settings[name]))
        if name=='botsort-reid':torch.set_num_threads(4)
        cap = cv2.VideoCapture(str(video)) if name.startswith('botsort') else None
        if cap:
            cap.set(cv2.CAP_PROP_POS_FRAMES, rows[0]['frame_index'])
        association_s = decode_s = 0.
        mismatches = []
        identities = set()
        started = time.perf_counter()
        try:
            with (output/(name+'-observations.jsonl')).open('w') as stream:
                for row in rows:
                    frame = None
                    if cap:
                        before = time.perf_counter()
                        while round(cap.get(cv2.CAP_PROP_POS_FRAMES)) <= row['frame_index']:
                            ok, frame = cap.read()
                            if not ok:
                                raise ValueError('Source decoding ended early')
                        if frame is None or round(cap.get(cv2.CAP_PROP_POS_FRAMES))-1 != row['frame_index']:
                            raise ValueError('Exact source frame unavailable')
                        decode_s += time.perf_counter()-before
                    detections = row['detections']
                    boxes = np.asarray([[*d['bbox_xyxy'], d['confidence'], d['class_id']] for d in detections], dtype=np.float32).reshape(-1, 6)
                    width, height = events['source_size_px']
                    before = time.perf_counter()
                    tracks = tracker.update(Boxes(boxes, (height, width)), img=frame)
                    association_s += time.perf_counter()-before
                    observations = []
                    for track in tracks:
                        idx, identity = int(track[-1]), int(track[4])
                        d = detections[idx]
                        observations.append({'track_id': identity, 'detection_index': idx,
                                             'pixel': d['pixel'], 'bbox_xyxy': d['bbox_xyxy'],
                                             'confidence': d['confidence']})
                        identities.add(identity)
                    if name == 'bytetrack':
                        pairs = lambda obs: sorted((o['track_id'], o['detection_index']) for o in obs)
                        if pairs(observations) != pairs(row['tracked_observations']):
                            mismatches.append(row['frame_index'])
                    stream.write(json.dumps({'frame_index': row['frame_index'], 'time_s': row['time_s'], 'detections': detections, 'tracked_observations': observations})+'\n')
        finally:
            if cap:
                cap.release()
        results[name] = {'samples': len(rows), 'association_seconds': association_s,
                         'decode_seconds': decode_s, 'wall_seconds': time.perf_counter()-started,
                         'local_track_count': len(identities), 'physical_identity_accuracy': None,
                         'baseline_mismatch_frames': mismatches if name == 'bytetrack' else None}
        if mismatches:
            (output/'failure.json').write_text(json.dumps(results, indent=2))
            raise ValueError('ByteTrack replay differs; do not interpret comparison')
    (output/'result.json').write_text(json.dumps(results, indent=2))
    return results


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['reference', 'video', 'output']:
        parser.add_argument('--'+name, required=True)
    parser.add_argument('--allow-partial', action='store_true', help='Compare a committed immutable prefix, without calling it a complete match')
    parser.add_argument('--candidate', choices=['botsort', 'botsort-reid', 'ocsort'], default='botsort')
    parser.add_argument('--reid-checkpoint', type=Path)
    args = parser.parse_args()
    print(json.dumps(run(args.reference, args.video, args.output, allow_partial=args.allow_partial,
                         candidate=args.candidate,reid_checkpoint=args.reid_checkpoint), indent=2))
