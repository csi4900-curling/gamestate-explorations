"""Upstream learned stone detection, independent of colour and camera crop rules.

Boxes are object observations, not stone identities or cap/contact-point estimates.
The default operating confidence is the upstream predict default, not calibrated
confidence. Callers must record any operating-point change in experiment metadata.
"""
from pathlib import Path
import hashlib
import time


class StoneDetector:
    def __init__(self, checkpoint, *, device='cpu', threads=4, backend='pytorch', export=None, head='checkpoint'):
        if head not in ('checkpoint', 'end2end', 'conventional'):
            raise ValueError('Unknown detector head policy')
        if head != 'checkpoint' and backend != 'pytorch':
            raise ValueError('Explicit head selection currently requires PyTorch; static exports retain their exported head')
        if not isinstance(threads, int) or isinstance(threads, bool) or threads < 1:
            raise ValueError('Detector threads must be a positive integer')
        import torch
        import ultralytics
        from ultralytics import YOLO
        self.threads = threads
        self.model = YOLO(str(checkpoint))
        self.requested_head = None if head == 'checkpoint' else head == 'end2end'
        if self.requested_head is not None:
            self.model.overrides['end2end'] = self.requested_head
        self.device = device
        self.imgsz = self.model.ckpt.get('train_args', {}).get('imgsz')
        if self.imgsz is None:
            raise ValueError('Checkpoint must declare inference input size or adapter must be explicitly configured')
        self.provenance = {'backend': 'ultralytics.YOLO.predict', 'ultralytics': ultralytics.__version__,
                           'torch': torch.__version__, 'device': device, 'threads': threads,
                           'checkpoint_sha256': hashlib.sha256(Path(checkpoint).read_bytes()).hexdigest(),
                           'imgsz': self.imgsz, 'imgsz_source': 'checkpoint train_args',
                           'classes': self.model.names, 'point_semantics': 'body_box_center_not_cap_or_ground_contact'}
        self.provenance['head_policy'] = head
        self.provenance['checkpoint_end2end'] = bool(self.model.model.end2end)
        self.requested_execution_device = None
        if backend == 'openvino_gpu':
            import openvino as ov
            if export is None: raise ValueError('OpenVINO requires an explicit exported model directory')
            core = ov.Core()
            if 'GPU' not in core.available_devices: raise ValueError('Requested OpenVINO GPU unavailable; refusing CPU fallback')
            export = Path(export)
            xmls = list(export.glob('*.xml'))
            if len(xmls) != 1: raise ValueError('Expected exactly one OpenVINO model XML')
            shape = list(core.read_model(xmls[0]).input().shape)
            if len(shape) != 4 or shape[:2] != [1,3]: raise ValueError('Expected static batch-one RGB export')
            self.imgsz = shape[2:]
            self.device = 'intel:gpu'
            self.requested_execution_device = 'GPU'
            self.model = YOLO(str(export), task='detect')
            self.provenance.update(backend='ultralytics.YOLO.predict/openvino_gpu',device=self.device,
                openvino=ov.__version__, device_name=core.get_property('GPU','FULL_DEVICE_NAME'),
                imgsz=self.imgsz,imgsz_source='static OpenVINO exported input shape',
                export_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in export.iterdir() if p.is_file()},
                precision='upstream OpenVINO LATENCY defaults; numerical predictions may differ from PyTorch')
        elif backend != 'pytorch' or export is not None:
            raise ValueError('Unsupported detector backend/export combination')
        # Upstream setup_model/select_device may reset PyTorch's process-global
        # thread setting. Its supported callback runs after setup and before
        # prediction, including on the first call.
        self.model.add_callback('on_predict_start', self._configure_prediction_threads)
        self.provenance['thread_policy'] = 'Set requested threads in upstream on_predict_start; restore caller setting after prediction'

    def _configure_prediction_threads(self, predictor):
        import torch
        torch.set_num_threads(self.threads)
        self._effective_threads = torch.get_num_threads()

    def detect(self, frame, *, confidence=0.25):
        import torch
        started = time.perf_counter()
        previous_threads = torch.get_num_threads()
        self._effective_threads = None
        try:
            prediction = self.model.predict(frame, imgsz=self.imgsz, conf=confidence,
                                            device=self.device, verbose=False)[0]
        finally:
            torch.set_num_threads(previous_threads)
        if self._effective_threads != self.threads:
            raise RuntimeError('Upstream prediction did not apply the requested thread setting')
        if self.requested_head is not None and bool(self.model.predictor.model.end2end) != self.requested_head:
            raise RuntimeError('Requested detector head was not selected by the upstream predictor')
        if self.requested_execution_device:
            execution = self.model.predictor.model.backend.ov_compiled_model.get_property('EXECUTION_DEVICES')
            if not any(str(d).startswith(self.requested_execution_device) for d in execution):
                raise RuntimeError(f'Requested GPU but execution devices are {execution}')
        boxes = []
        for xyxy, score, cls in zip(prediction.boxes.xyxy.cpu().tolist(),
                                   prediction.boxes.conf.cpu().tolist(), prediction.boxes.cls.cpu().tolist()):
            x1,y1,x2,y2 = xyxy
            boxes.append({'bbox_xyxy': xyxy, 'pixel': [(x1+x2)/2,(y1+y2)/2],
                          'confidence': score, 'class_id': int(cls),
                          'class_name': self.model.names[int(cls)], 'colour': None,
                          'physical_identity': None, 'point_semantics': 'body_box_center_not_cap_or_ground_contact'})
        return {'detections': boxes, 'wall_seconds': time.perf_counter()-started,
                'upstream_speed_ms': prediction.speed, 'confidence_threshold': confidence,
                'effective_torch_threads': self._effective_threads,
                'confidence_calibrated': False}
