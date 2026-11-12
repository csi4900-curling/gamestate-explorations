"""Replay identical upstream association/line logic for a detector backend probe.

This is a component comparison, not the public integrated-pipeline benchmark.
Reference detections are immutable saved observations; no reference event labels
or per-recording inference rules are supplied to either detector.
"""
import argparse
import json
import time
from pathlib import Path
from types import SimpleNamespace
import cv2
import numpy as np
from prototype.learned_event_pipeline import digest
from prototype.line_crossing_events import LineCrossings, validate_config


def replay(rows, config, tracker_settings, size):
    from ultralytics.trackers.byte_tracker import BYTETracker
    from ultralytics.engine.results import Boxes
    tracker = BYTETracker(SimpleNamespace(**tracker_settings))
    crossing = LineCrossings(config)
    width, height = size
    for row in rows:
        detections = row['detections']
        boxes = np.asarray([[*d['bbox_xyxy'], d['confidence'], d['class_id']]
                            for d in detections], dtype=np.float32).reshape(-1, 6)
        tracks = tracker.update(Boxes(boxes, (height, width)))
        observations = []
        for tr in tracks:
            index = int(tr[-1]); d = detections[index]; x, y = d['pixel']
            observations.append({'track_id': int(tr[4]), 'point_normalized': [x/width,y/height],
                                 'pixel': [x,y], 'bbox_xyxy': d['bbox_xyxy'],
                                 'confidence': d['confidence'], 'detection_index': index})
        crossing.update(observations, row['time_s'])
    return crossing.events


def run(video, reference, model, output, start, end, config_path):
    import openvino as ov
    import torch
    from ultralytics import YOLO
    video, reference, model, output = map(Path, (video, reference, model, output))
    protocol = json.loads((reference/'protocol.json').read_text())
    config = validate_config(json.loads(Path(config_path).read_text()))
    if digest(video) != protocol['source_sha256']:
        raise ValueError('Reference/video mismatch')
    if digest(config_path) != protocol['config_sha256'] or config != json.loads((reference/'config.json').read_text()):
        raise ValueError('Reference configuration changed')
    core = ov.Core()
    if 'GPU' not in core.available_devices:
        raise ValueError('GPU required; no silent CPU fallback')
    if output.exists(): raise ValueError('Preserve previous comparison')
    output.mkdir(parents=True)
    source_rows = [json.loads(line) for line in (reference/'observations.jsonl').open()]
    source_rows = [r for r in source_rows if start <= r['time_s'] < end]
    if not source_rows: raise ValueError('No reference observations in requested interval')
    if any(b['frame_index']-a['frame_index'] != protocol['sample_step_frames']
           for a,b in zip(source_rows,source_rows[1:])):
        raise ValueError('Reference sampling gap')
    metadata = {'development': True, 'public_pipeline_evaluated': False,
                'source_sha256': protocol['source_sha256'], 'source_interval_s': [start,end],
                'reference_observations_sha256': digest(reference/'observations.jsonl'),
                'reference_protocol': protocol, 'config': config,
                'export_hashes': {p.name:digest(p) for p in model.iterdir() if p.is_file()},
                'code_sha256': {p.name:digest(p) for p in [Path(__file__),
                    Path(__file__).with_name('line_crossing_events.py')]},
                'comparison': 'Same saved source frames, upstream ByteTrack and configured LineCrossings; GPU vs saved CPU detections',
                'runtime_context': 'Concurrent workloads; not isolated throughput'}
    (output/'protocol.json').write_text(json.dumps(metadata,indent=2)+'\n')
    xml = next(model.glob('*.xml')); shape = list(core.read_model(xml).input().shape)
    torch.set_num_threads(4)
    detector = YOLO(model, task='detect'); cap = cv2.VideoCapture(str(video)); rows=[]
    try:
        with (output/'observations.jsonl').open('w') as stream:
            for source in source_rows:
                index=source['frame_index']; cap.set(cv2.CAP_PROP_POS_FRAMES,index)
                ok,frame=cap.read()
                if not ok or round(cap.get(cv2.CAP_PROP_POS_FRAMES))-1 != index:
                    raise ValueError('Exact source frame unavailable')
                started=time.perf_counter()
                prediction=detector.predict(frame,imgsz=shape[2:],conf=config['detector_confidence'],device='intel:gpu',verbose=False)[0]
                duration=time.perf_counter()-started
                execution=detector.predictor.model.backend.ov_compiled_model.get_property('EXECUTION_DEVICES')
                if not any(str(x).startswith('GPU') for x in execution): raise ValueError('Unexpected CPU fallback')
                detections=[]
                for x1,y1,x2,y2,score,cls in prediction.boxes.data.cpu().tolist():
                    detections.append({'bbox_xyxy':[x1,y1,x2,y2],'pixel':[(x1+x2)/2,(y1+y2)/2],
                                       'confidence':score,'class_id':int(cls)})
                row={'time_s':source['time_s'],'frame_index':index,'detections':detections,
                     'wall_seconds':duration,'execution_devices':execution}
                stream.write(json.dumps(row)+'\n');stream.flush();rows.append(row)
    finally: cap.release()
    settings=protocol['tracker_config'];size=protocol['source_size_px']
    result={**metadata,'cpu_events':replay(source_rows,config,settings,size),
            'gpu_events':replay(rows,config,settings,size),'sampled_frames':len(rows),
            'gpu_wall_seconds':sum(r['wall_seconds'] for r in rows),
            'physical_delivery_accuracy_measured':False,'complete_pipeline_equivalence_verified':False}
    (output/'result.json').write_text(json.dumps(result,indent=2)+'\n')


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('video','reference','model','output','config'):p.add_argument('--'+name,required=True)
    p.add_argument('--start',required=True,type=float);p.add_argument('--end',required=True,type=float)
    a=p.parse_args();run(a.video,a.reference,a.model,a.output,a.start,a.end,a.config)
