"""Compare upstream YOLO end-to-end and conventional heads on identical images."""
import argparse
import hashlib
import json
from pathlib import Path
import time


def run_sequence(video, reference_run, checkpoint, output):
    """Exercise the existing event scanner twice, changing only the upstream head.

    Dependency replacement is confined to this comparison process. The public
    scanner, ByteTrack, line logic and live benchmark files remain unchanged.
    """
    from unittest.mock import patch
    from prototype import learned_event_pipeline as pipeline
    from prototype.stone_detector import StoneDetector
    from prototype.detection_cache import digest
    reference_run, checkpoint, output = map(Path, (reference_run, checkpoint, output))
    reference = json.loads((reference_run/'events.json').read_text())
    if digest(video) != reference['source_sha256']:
        raise ValueError('Reference source differs')
    if digest(checkpoint) != reference['model']['checkpoint_sha256']:
        raise ValueError('Reference checkpoint differs')
    if output.exists():
        raise ValueError('Preserve prior comparison')
    output.mkdir(parents=True)
    config = json.loads((reference_run/'config.json').read_text())
    config['tracker_config'] = 'tracker.yaml'
    (output/'config.json').write_text(json.dumps(config, indent=2))
    (output/'tracker.yaml').write_bytes((reference_run/'tracker.yaml').read_bytes())
    (output/'adapter.py').write_bytes(Path(__file__).read_bytes())
    manifest = {'development': True, 'source_sha256': reference['source_sha256'],
                'interval_s': reference['source_interval_s'], 'threads': 1,
                'comparison': 'Two fresh PyTorch runs: same public event scanner, source sampling, checkpoint, confidence and ByteTrack configuration; only upstream head differs.',
                'reference_gpu_predictions_not_used_for_head_effect': True,
                'scope': 'Detector/event/association component comparison; geometry and dense tracking not run.',
                'input_hashes': {str(p.resolve()): digest(p) for p in
                                [reference_run/'events.json', reference_run/'config.json', reference_run/'tracker.yaml', checkpoint, Path(__file__), Path(pipeline.__file__)]}}
    (output/'comparison-protocol.json').write_text(json.dumps(manifest, indent=2))
    for mode in [True, False]:
        class ComparedDetector(StoneDetector):
            def __init__(self, checkpoint, **kwargs):
                super().__init__(checkpoint, threads=1, **kwargs)
                self.model.overrides['end2end'] = mode
                self.provenance['experimental_upstream_end2end'] = mode

            def detect(self, frame, **kwargs):
                result = super().detect(frame, **kwargs)
                if bool(self.model.predictor.model.end2end) != mode:
                    raise ValueError('Requested upstream head not selected')
                return result

        with patch.object(pipeline, 'StoneDetector', ComparedDetector):
            pipeline.run(video, output/('end2end' if mode else 'conventional'), output/'config.json', checkpoint,
                         start=reference['source_interval_s'][0], end=reference['source_interval_s'][1],
                         source_id=reference['source_id'])
    (output/'finished.json').write_text(json.dumps({'status': 'processed', 'accuracy_verified': False}))


def run(checkpoint, inputs, output, confidence):
    import cv2
    import torch
    import ultralytics
    from ultralytics import YOLO
    checkpoint, inputs, output = map(Path, (checkpoint, inputs, output))
    if output.exists():
        raise ValueError('Preserve prior comparison')
    items = json.loads(inputs.read_text())['items']
    images = {}
    for item in items:
        p = Path(item['image'])
        if hashlib.sha256(p.read_bytes()).hexdigest() != item['image_sha256']:
            raise ValueError('Input image hash mismatch')
        images[str(p)] = item['image_sha256']
    output.mkdir(parents=True)
    torch.set_num_threads(1)
    protocol = {'development': True, 'ultralytics': ultralytics.__version__,
                'checkpoint_sha256': hashlib.sha256(checkpoint.read_bytes()).hexdigest(),
                'inputs_sha256': hashlib.sha256(inputs.read_bytes()).hexdigest(),
                'adapter_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                'images': images, 'confidence': confidence, 'threads': 1,
                'scope': 'Upstream heads compared without tuning; counts are not accuracy. CPU timings include concurrent workload.',
                'production_changed': False}
    (output/'protocol.json').write_text(json.dumps(protocol, indent=2))
    (output/'adapter.py').write_bytes(Path(__file__).read_bytes())
    results = []
    for end2end in [True, False]:
        model = YOLO(str(checkpoint))
        size = model.ckpt['train_args']['imgsz']
        for path, digest in images.items():
            image = cv2.imread(path)
            started = time.perf_counter()
            pred = model.predict(image, imgsz=size, conf=confidence, end2end=end2end,
                                 device='cpu', verbose=False)[0]
            actual = bool(model.predictor.model.end2end)
            if actual != end2end:
                raise ValueError('Requested upstream head was not selected')
            result = {'image': path, 'image_sha256': digest, 'end2end': actual,
                      'imgsz': size, 'iou': model.predictor.args.iou,
                      'wall_seconds': time.perf_counter()-started, 'upstream_speed_ms': pred.speed,
                      'boxes': pred.boxes.data.cpu().tolist()}
            results.append(result)
            with (output/'observations.jsonl').open('a') as stream:
                stream.write(json.dumps(result)+'\n')
            print(json.dumps({'image': path, 'end2end': actual, 'boxes': len(result['boxes'])}), flush=True)
        del model
    (output/'summary.json').write_text(json.dumps({'frames_per_head': len(images), 'results': results}, indent=2))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--checkpoint', required=True)
    p.add_argument('--inputs')
    p.add_argument('--video')
    p.add_argument('--reference-run')
    p.add_argument('--output', required=True)
    p.add_argument('--confidence', type=float)
    a = p.parse_args()
    if a.reference_run:
        if not a.video or a.inputs or a.confidence is not None:
            p.error('Sequence comparison needs --video and uses the reference confidence')
        run_sequence(a.video, a.reference_run, a.checkpoint, a.output)
    else:
        if not a.inputs or a.confidence is None:
            p.error('Image comparison needs --inputs and --confidence')
        run(a.checkpoint, a.inputs, a.output, a.confidence)
