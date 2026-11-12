"""App-owned calibration frames, preview attempts and immutable confirmations."""
from pathlib import Path
import copy
import json
import math
import time
import uuid
import shutil
import platform
import importlib.metadata

import cv2
import numpy as np

from prototype.rink_calibration import SCHEMA, POLICY, digest, fit_panel, landmarks, marking_types, validate_interval, verify_sealed_panel


def write(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix+'.tmp')
    temp.write_text(json.dumps(value, indent=2, allow_nan=False)+'\n'); temp.replace(path)


class CalibrationStore:
    def __init__(self, app):
        self.app = app
        self.root = app.data/'calibrations'
        for folder in ['frames', 'previews', 'confirmed']:
            (self.root/folder).mkdir(parents=True, exist_ok=True)

    def options(self):
        return {'schema_version': SCHEMA, 'policy': POLICY,
                'landmarks': {panel: landmarks(panel) for panel in ['left', 'right']},
                'marking_types': {panel: marking_types(panel) for panel in ['left', 'right']},
                'learned_rink_model_available': False,
                'physical_camera_model':'Pinhole with panel-centred principal point, square pixels, zero skew and no lens distortion. Static fit and withheld markings must support the same camera used for stone-height projection.',
                'origin': 'Explicit operator calibration required; no validated independent learned rink-position model.'}

    def frame(self, request):
        video = self.app.video(request['video_id'])
        requested = float(request['time_s'])
        if not math.isfinite(requested) or not 0 <= requested < video['duration_s']:
            raise ValueError('Choose a calibration frame inside the source video')
        cap = cv2.VideoCapture(video['path'])
        index = round(requested * video['fps'])
        if index >= round(video['duration_s']*video['fps']):
            raise ValueError('Calibration frame is beyond the recording')
        try:
            cap.set(cv2.CAP_PROP_POS_FRAMES, index)
            ok, image = cap.read()
            if not ok or round(cap.get(cv2.CAP_PROP_POS_FRAMES))-1 != index:
                raise ValueError('Source frame could not be decoded at the requested timestamp')
        finally:
            cap.release()
        identifier = uuid.uuid4().hex[:12]
        path = self.root/'frames'/(identifier+'.png')
        if not cv2.imwrite(str(path), image):
            raise ValueError('Could not save source calibration frame')
        record = {'id': identifier, 'source_sha256': video['source_sha256'], 'video_id': video['id'],
                  'frame_index': index, 'time_s': index/video['fps'], 'requested_time_s': requested,
                  'size_px': [image.shape[1], image.shape[0]], 'image_path': str(path.resolve()),
                  'image_url': self.app.file_url(path), 'image_sha256': digest(path)}
        write(path.with_suffix('.json'), record)
        return record

    def preview(self, request):
        video = self.app.video(request['video_id'])
        if digest(video['path']) != video['source_sha256']:
            raise ValueError('Recording changed after loading; reload the source')
        interval = list(map(float, request['valid_interval_s']))
        if len(interval) != 2 or not all(math.isfinite(x) for x in interval) or not 0 <= interval[0] < interval[1] <= video['duration_s']:
            raise ValueError('Invalid camera-pose interval')
        if set(request.get('panels', {})) != {'left', 'right'}:
            raise ValueError('Calibrate both cameras')
        result = {'id': uuid.uuid4().hex[:12], 'schema_version': SCHEMA, 'status': 'checks_passed',
                  'created_at': time.time(), 'source_sha256': video['source_sha256'],
                  'video_id': video['id'], 'valid_interval_s': interval, 'panels': {},
                  'policy': POLICY, 'absolute_accuracy_verified': False,
                  'fitter_sha256': digest(Path(__file__).with_name('rink_calibration.py')),
                  'physical_camera_fitter_sha256':digest(Path(__file__).with_name('pinhole_calibration.py')),
                  'template_generator_sha256':digest(Path(__file__).with_name('rink_template.py')),
                  'fit_runtime': {'python':platform.python_version(),'opencv':cv2.__version__,'numpy':np.__version__,'scipy':importlib.metadata.version('scipy')},
                  'prediction_visible_during_annotation': bool(request.get('prediction_visible_during_annotation', True))}
        for panel, spec in request['panels'].items():
            frame_id = self.app.identifier(spec['frame_id'])
            frame = json.loads((self.root/'frames'/(frame_id+'.json')).read_text())
            if frame['source_sha256'] != video['source_sha256'] or digest(frame['image_path']) != frame['image_sha256']:
                raise ValueError('Calibration frame is changed or belongs to another recording')
            try:
                if 'template_parameters' in spec:
                    from prototype.rink_template import template_panel
                    fitted=template_panel(spec['template_parameters'],panel)
                else:
                    fitted = fit_panel(spec, panel)
                    from prototype.pinhole_calibration import refine_camera
                    fitted = refine_camera(fitted)
            except (ValueError, TypeError, KeyError, cv2.error, np.linalg.LinAlgError) as exc:
                fitted = {'panel': panel, 'status': 'rejected', 'reasons': [str(exc)]}
            if fitted['status']=='checks_passed':
                if fitted.get('calibration_method')=='operator_template_alignment_v1':
                    from prototype.calibrated_camera_geometry import panel_features,register
                    features=panel_features(cv2.resize(cv2.imread(frame['image_path']),(1920,1080)),panel)
                    matrix,pose=register(features,features)
                    supported=matrix is not None
                else:
                    from prototype.calibration_pose import PoseVerifier
                    supported,pose=PoseVerifier(cv2.imread(frame['image_path']),fitted,panel).check(cv2.imread(frame['image_path']),details=True)
                fitted['reference_pose_support']=pose
                if not supported:
                    fitted['status']='rejected';fitted['reasons'].append('Choose a clearer frame with distributed static image features; camera reuse cannot be verified from this reference')
            fitted['frame'] = frame
            result['panels'][panel] = fitted
            if fitted['status'] != 'checks_passed':
                result['status'] = 'rejected'
        write(self.root/'previews'/(result['id']+'.json'), result)
        return result

    def confirm(self, request):
        if request.get('confirmed') is not True:
            raise ValueError('Inspect the projected markings and confirm the calibration')
        reviewer = str(request.get('reviewer', '')).strip()
        if not reviewer or len(reviewer) > 100:
            raise ValueError('Record the calibration operator name')
        kind = request.get('operator_kind', 'human')
        if kind not in ['human', 'agent']:
            raise ValueError('Operator kind must be human or agent')
        preview_id = self.app.identifier(request['preview_id'])
        preview = json.loads((self.root/'previews'/(preview_id+'.json')).read_text())
        if preview['status'] != 'checks_passed':
            raise ValueError('Calibration failed its checks; correct the landmarks before saving')
        for panel in preview['panels'].values():
            verify_sealed_panel(panel)
            if not panel.get('camera_model'):
                raise ValueError('Re-preview calibration to fit a consistent physical camera')
            if digest(panel['frame']['image_path'])!=panel['frame']['image_sha256']:
                raise ValueError('Calibration frame changed since preview')
        video = self.app.video(preview['video_id'])
        if digest(video['path']) != preview['source_sha256']:
            raise ValueError('Recording changed since calibration preview')
        identifier = uuid.uuid4().hex[:12]
        record = {**preview, 'id': identifier, 'preview_id': preview_id, 'status': 'confirmed',
                  'confirmed_at': time.time(), 'reviewer': reviewer, 'operator_kind': kind,
                  'confirmation_scope': 'Operator reviewed the saved source calibration and overlay. Template placement is visual alignment only; point mode retains its separate marking checks. Neither is independent trajectory ground truth.',
                  'overlay_visible_during_confirmation': True}
        write(self.root/'confirmed'/(identifier+'.json'), record)
        return record

    def list(self, video_id):
        source = self.app.video(video_id)['source_sha256']
        rows = [json.loads(p.read_text()) for p in (self.root/'confirmed').glob('*.json')]
        rows = [r for r in rows if r['source_sha256'] == source]
        for row in rows:
            try:
                for panel in row['panels'].values():verify_sealed_panel(panel)
                row['evidence_integrity']='verified'
            except (ValueError, KeyError, TypeError):row['evidence_integrity']='needs_repreview'
        return sorted(rows, key=lambda r: r['confirmed_at'], reverse=True)

    def selected(self, identifiers, source_sha256, interval):
        if not identifiers:
            raise ValueError('Calibration required: check and save both camera mappings before analysis')
        if len(identifiers) != len(set(identifiers)):
            raise ValueError('Select each calibration only once')
        assets = [json.loads((self.root/'confirmed'/(self.app.identifier(i)+'.json')).read_text()) for i in identifiers]
        validate_interval(assets, interval, source_sha256)
        for asset in assets:
            for panel in asset['panels'].values():
                verify_sealed_panel(panel)
                if digest(panel['frame']['image_path']) != panel['frame']['image_sha256']:
                    raise ValueError('Saved calibration source frame has changed')
        return assets

    def snapshot(self, assets, output, source_sha256, interval):
        saved = copy.deepcopy(assets)
        folder = Path(output)/'calibration-frames'; folder.mkdir()
        for asset in saved:
            for name, panel in asset['panels'].items():
                source = panel['frame']['image_path']
                target = folder/(asset['id']+'-'+name+'.png')
                shutil.copyfile(source, target)
                panel['frame']['image_path'] = str(target.relative_to(output))
                panel['frame'].pop('image_url', None)
        path = Path(output)/'camera-calibration.json'
        write(path, {'schema_version': 'source-calibration-bundle-v1', 'source_sha256': source_sha256,
                     'source_interval_s': interval, 'calibrations': saved,
                     'manual_calibration_explicit': True, 'physical_accuracy_verified': False})
        return path
