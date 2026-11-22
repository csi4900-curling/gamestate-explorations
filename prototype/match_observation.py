"""Shared match observations: detected boards, conditional geometry and OCR totals.

ByteTrack IDs remain camera observations, never certified physical stone identities.
Calibration is transferred from the original fixed references by existing registration;
no new landmark selection, ring gate or per-event calibration fit is introduced.
"""
import hashlib
import json
import sys
import time
import importlib.metadata
from pathlib import Path
import cv2
import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parent))
from body_localization import feature_heights, transported_reference_camera, localize, project
from prototype.scoreboard_observation import ScoreboardObserver


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()


def project_body(H,pixel,region,prior,heights):
    raw=None
    try:
        if H is not None:raw=project(H,[pixel])[0]
        q,correction=localize(H,pixel,region,'body_box_center',camera_prior=prior,heights_m=heights) if prior is not None else (None,{'status':'unavailable'})
    except (ValueError,np.linalg.LinAlgError,FloatingPointError) as exc:
        q=None;correction={'status':'undefined_projection','reason':str(exc)}
    return (raw.tolist() if raw is not None and np.isfinite(raw).all() else None,
            q.tolist() if q is not None and np.isfinite(q).all() else None,correction)


class MatchObserver:
    def __init__(self,config_path,output):
        self.config_path=Path(config_path).resolve()
        self.config=json.loads(self.config_path.read_text());self.output=Path(output)
        cfg=self.config
        geometry_threads=cfg.get('geometry_opencv_threads')
        if geometry_threads is not None:
            if isinstance(geometry_threads,bool) or not isinstance(geometry_threads,int) or geometry_threads<1:
                raise ValueError('Geometry OpenCV threads must be a positive integer')
            cv2.setNumThreads(geometry_threads)
        if cfg.get('schema_version')!='match-observation-v1':raise ValueError('Unsupported match observation config')
        self.interval=float(cfg['score_sample_interval_s'])
        if not np.isfinite(self.interval) or self.interval<=0:raise ValueError('Positive score interval required')
        resolve=lambda p:(self.config_path.parent/p).resolve()
        geometry_mode=cfg.get('geometry_mode','direct_low_resolution_reference_registration')
        self.heights=feature_heights(cfg.get('feature_heights_m'))
        self.calibration_coverage={panel:{'frames':0,'registered_frames':0,'unsupported_stone_points':0} for panel in ('left','right')}
        self.calibration_gaps={panel:[] for panel in ('left','right')}
        self.open_calibration_gaps={panel:None for panel in ('left','right')}
        if geometry_mode=='explicit_source_calibration_v1':
            from prototype.rink_calibration import load_bundle
            bundle_path=resolve(cfg['source_calibration_bundle'])
            bundle=load_bundle(bundle_path)
            self.files=[bundle_path]+[(bundle_path.parent/p['frame']['image_path']).resolve()
                for asset in bundle['calibrations'] for p in asset['panels'].values()]
            self.references={panel:(None,None,(0,0,320,360) if panel=='left' else (320,0,640,360),None)
                             for panel in ('left','right')}
            annotations={'method':'Explicit operator-selected source rink markings',
                         'coordinate_convention':'Tee origin, +x camera-right, +y foreground; signed hog coordinates in config'}
        else:
            from camera_geometry import features
            calibration_path=resolve(cfg['calibration']);annotations_path=resolve(cfg['reference_annotations'])
            self.heights=feature_heights(cfg.get('feature_heights_m'))
            calibration=json.loads(calibration_path.read_text());annotations=json.loads(annotations_path.read_text())
            self.references={};self.files=[calibration_path,annotations_path]
            for panel in ('left','right'):
                spec=annotations['views'][panel];path=resolve(cfg['reference_frames'])/spec['reference_frame']
                native=cv2.imread(str(path))
                if native is None:raise ValueError(f'Cannot read geometry reference {path}')
                h,w=native.shape[:2];frame=cv2.resize(native,(640,360))
                region=(0,0,320,360) if panel=='left' else (320,0,640,360)
                H=np.asarray(calibration[panel]['refined_H'])@np.diag([w/640,h/360,1])
                self.references[panel]=(frame,H,region,features(frame,region))
                self.files.append(path)
        self.ocr=ScoreboardObserver(team_labels=cfg['scoreboard_team_labels'],
            model_dir=resolve(cfg['ocr_model_dir']),crop_normalized=cfg['scoreboard_crop_normalized'])
        self.geometry=None
        geometry_mode=cfg.get('geometry_mode','direct_low_resolution_reference_registration')
        if geometry_mode=='explicit_source_calibration_v1':
            from prototype.calibrated_camera_geometry import CalibratedCameraGeometry
            self.geometry=CalibratedCameraGeometry(bundle_path,alignment=cfg.get('camera_alignment','locked'),
                foreground_checkpoint=resolve(cfg['camera_foreground_checkpoint']) if cfg.get('camera_foreground_checkpoint') else None,
                foreground_sha256=cfg.get('camera_foreground_sha256'),
                fast_scale=cfg.get('registration_fast_scale'),
                fast_nfeatures=cfg.get('registration_fast_nfeatures', 1200),
                parallel_panels=bool(cfg.get('registration_parallel_panels', False)))
            if cfg.get('camera_foreground_checkpoint'):self.files.append(resolve(cfg['camera_foreground_checkpoint']))
        elif geometry_mode=='original_split_geometry_with_anchor_reuse':
            from prototype.split_camera_geometry import SplitCameraGeometry
            self.geometry=SplitCameraGeometry(calibration_path,annotations_path,resolve(cfg['reference_frames']))
        elif geometry_mode in ('parallel_native_geometry_development_v1', 'parallel_native_geometry_development_v2'):
            from prototype.parallel_camera_geometry import ParallelNativeGeometry
            self.geometry=ParallelNativeGeometry(calibration_path,annotations_path,resolve(cfg['reference_frames']))
        elif geometry_mode!='direct_low_resolution_reference_registration':
            raise ValueError('Unknown geometry mode')
        self.next_score=None;self.last_score={};self.count=0;self.geometry_s=0;self.ocr_s=0;self.geometry_skipped_frames=0
        self.stream=(self.output/'match-observations.jsonl').open('w')
        self.score_stream=(self.output/'score-observations.jsonl').open('w')
        self.provenance={'config':cfg,'config_sha256':sha(self.config_path),
            'geometry_opencv_threads':cv2.getNumThreads(),
            'reference_sha256':{str(p):sha(p) for p in self.files},
            'calibration_origin':annotations['method'],'geometry_method':'Existing fixed reference calibration + baseline SIFT image registration; per-frame registration, no new calibration fits',
            'coordinate_system':annotations['coordinate_convention'],
            'identity_status':'Upstream tracker labels only; cross-view and physical identities unverified',
            'score_status':'Raw OCR observation; team labels configured metadata, not inferred from stone colour',
            'scope':'Development observation stage; does not replace dense CoTracker or establish complete trajectories'}
        if self.geometry is not None:
            self.provenance['geometry_method']='Original native departure registration; existing automatic receiving house/hog fit, followed by shared anchor registration across events. Legacy initializer heuristics retained.'
        if geometry_mode in ('parallel_native_geometry_development_v1', 'parallel_native_geometry_development_v2'):
            self.provenance['geometry_method']='Source parallel-boundary vanishing point and native paint/wheelchair constraints, followed by recording-local anchor registration in both views. No stone-fitted alignment or feed offset.'
        if geometry_mode=='explicit_source_calibration_v1':
            self.provenance['geometry_method']='Explicit source calibration and verified image registration; no automatic refit or unrelated reference mapping.'
            self.provenance['source_calibration_bundle_sha256']=sha(bundle_path)
            self.provenance['manual_calibration']=True
        self.provenance['ocr_versions']={p:importlib.metadata.version(p) for p in ('rapidocr','onnxruntime')}
        self.provenance['ocr_model_sha256']={p.name:sha(p) for p in resolve(cfg['ocr_model_dir']).glob('*.onnx')}
        if geometry_mode=='explicit_source_calibration_v1':
            code_names=('match_observation.py','scoreboard_observation.py','score_grid.py',
                        'body_localization.py','stone_measurement.py','rink_calibration.py',
                        'pinhole_calibration.py','rink_template.py','calibrated_camera_geometry.py',
                        'calibration_pose.py','camera_foreground.py')
        else:
            code_names=('match_observation.py','match_observation_report.py','scoreboard_observation.py','score_grid.py',
                        'camera_geometry.py','body_localization.py','stone_measurement.py','vision_core.py','rectification_core.py','automatic_house_calibration.py',
                        'split_camera_geometry.py','source_specific_house_calibration.py','split_house_ellipse_v2.py','split_house_reference.py','house_affine_transfer_audit.py')
            if geometry_mode in ('parallel_native_geometry_development_v1', 'parallel_native_geometry_development_v2'):
                code_names += ('parallel_camera_geometry.py',)
        code_names=tuple(name for name in code_names if Path(__file__).with_name(name).exists())
        self.provenance['code_sha256']={name:sha(Path(__file__).with_name(name)) for name in code_names}
        snapshot=self.output/'code-snapshot';snapshot.mkdir(exist_ok=True)
        for name in code_names:(snapshot/name).write_bytes(Path(__file__).with_name(name).read_bytes())
        (self.output/'match-observation-protocol.json').write_text(json.dumps(self.provenance,indent=2))

    def _record_ocr(self, frame, now):
        score = None
        if self.next_score is None or now + 1e-8 >= self.next_score:
            score = self.ocr.observe(frame, now)
            self.ocr_s += score['wall_seconds']
            self.next_score = now + self.interval
            self.score_stream.write(json.dumps(score) + '\n')
            self.score_stream.flush()
            for team, total in score['totals'].items():
                if total['value'] is not None:
                    self.last_score[team] = {'observed_at_s': now, **total}
        return score

    def _record_coverage(self, state):
        now = state['time_s']
        frame_index = state['frame_index']
        for panel, board in state['boards'].items():
            diag = board['registration']
            if diag.get('status') == 'geometry_skipped_inactive_interval':
                self.open_calibration_gaps[panel] = None
                continue
            coverage = self.calibration_coverage[panel]
            coverage['frames'] += 1
            registered = board['homography_normalized_pixels_to_local_metres'] is not None
            coverage['registered_frames'] += int(registered)
            coverage['unsupported_stone_points'] += sum(
                1 for s in board['stones']
                if (s.get('height_correction') or {}).get('status') == 'outside_calibration_support'
            )
            if not registered:
                gap = self.open_calibration_gaps[panel]
                if gap is None or gap['status'] != diag['status']:
                    gap = {'panel': panel, 'start_s': now, 'end_s': now, 'first_frame': frame_index,
                           'last_frame': frame_index, 'sampled_frames': 0, 'status': diag['status'],
                           'reason': diag.get('reason')}
                    self.calibration_gaps[panel].append(gap)
                    self.open_calibration_gaps[panel] = gap
                gap['end_s'] = now
                gap['last_frame'] = frame_index
                gap['sampled_frames'] += 1
            else:
                self.open_calibration_gaps[panel] = None

    def write_state(self, state, frame=None):
        now = state['time_s']
        if frame is not None and state.get('score_observation') is None and (self.next_score is None or now + 1e-8 >= self.next_score):
            state['score_observation'] = self._record_ocr(frame, now)
        self._record_coverage(state)
        state['last_observed_totals'] = {k: {**v, 'age_s': now - v['observed_at_s']} for k, v in self.last_score.items()}
        self.stream.write(json.dumps(state) + '\n')
        self.count += 1
        if self.count % 25 == 0:
            self.stream.flush()
        return state

    def observe_skipped(self, row, source_size_px, *, frame=None, write_stream=True):
        now = row['time_s']
        w, h = source_size_px
        from prototype.stone_measurement import body_point_support
        track_by_det = {t['detection_index']: t['track_id'] for t in row['tracked_observations']}
        boards = {}
        for panel in self.references:
            stones = []
            for detection_index, d in enumerate(row['detections']):
                x, _ = d['pixel']
                if (x < w / 2) != (panel == 'left'):
                    continue
                support = body_point_support(d, [w, h])
                stones.append({**d, 'tracker_id': track_by_det.get(detection_index),
                               'body_point_support': support,
                               'physical_identity': None, 'team': None,
                               'ice_plane_local_m': None, 'height_adjusted_local_m': None,
                               'height_correction': {'status': 'geometry_skipped_inactive_interval',
                                                     'reason': 'Outside scheduled active throw and probe windows'}})
            boards[panel] = {
                'stones': stones,
                'registration': {'status': 'geometry_skipped_inactive_interval',
                                 'reason': 'Outside scheduled active throw and probe windows',
                                 'calibration_refitted': False, 'physical_accuracy_verified': False},
                'homography_normalized_pixels_to_local_metres': None,
                'complete_board_verified': False, 'end_identity': None,
            }
        self.geometry_skipped_frames += 1
        score = self._record_ocr(frame, now) if frame is not None else None
        state = {'time_s': now, 'frame_index': row['frame_index'], 'boards': boards,
                 'score_observation': score,
                 'last_observed_totals': {k: {**v, 'age_s': now - v['observed_at_s']} for k, v in self.last_score.items()},
                 'current_end': None, 'current_points_from_stones': None,
                 'physical_identity_verified': False}
        if write_stream:
            self._record_coverage(state)
            self.stream.write(json.dumps(state) + '\n')
            self.count += 1
            if self.count % 25 == 0:
                self.stream.flush()
        return state

    def observe(self,frame,row,*,write_stream=True,run_ocr=True):
        now=row['time_s'];started=time.perf_counter();normalized=cv2.resize(frame,(640,360))
        boards={};h,w=frame.shape[:2]
        registered=self.geometry.observe(frame,now) if self.geometry is not None else None
        track_by_det={t['detection_index']:t['track_id'] for t in row['tracked_observations']}
        from prototype.stone_measurement import body_point_support
        for panel,(reference,H,region,desc) in self.references.items():
            if registered is not None:
                target,diag,prior=registered[panel]
            else:
                from camera_geometry import transfer
                target,diag=transfer(reference,normalized,H,region,reference_features=desc)
                try:
                    prior=transported_reference_camera(H,target,region) if target is not None else None
                except (ValueError,np.linalg.LinAlgError,FloatingPointError) as exc:
                    prior=None;diag={**diag,'height_prior_failure':str(exc)}
            stones=[]
            for detection_index,d in enumerate(row['detections']):
                x,y=d['pixel'];is_left=x<w/2
                if is_left!=(panel=='left'):continue
                pixel=np.asarray([x*640/w,y*360/h])
                support=body_point_support(d,[w,h])
                if self.provenance.get('manual_calibration') and not support['centre_supported']:
                    raw=q=None;correction={**support,'reason':'Clipped box midpoint is not the complete stone body centre'}
                elif hasattr(self.geometry,'point_supported') and not self.geometry.point_supported(panel,pixel):
                    raw=q=None;correction={'status':'outside_calibration_support','reason':'Missing alignment or point outside explicitly supported image region'}
                else:
                    raw,q,correction=project_body(target,pixel,region,prior,self.heights)
                stones.append({**d,'tracker_id':track_by_det.get(detection_index),
                    'body_point_support':support,
                    'physical_identity':None,'team':None,
                    'ice_plane_local_m':raw,'height_adjusted_local_m':q,
                    'height_correction':correction})
            boards[panel]={'stones':stones,'registration':diag,
                           'homography_normalized_pixels_to_local_metres':target.tolist() if target is not None else None,
                           'complete_board_verified':False,'end_identity':None}
        self.geometry_s+=time.perf_counter()-started
        score=self._record_ocr(frame,now) if run_ocr else None
        state={'time_s':now,'frame_index':row['frame_index'],'boards':boards,
               'score_observation':score,'last_observed_totals':{k:{**v,'age_s':now-v['observed_at_s']} for k,v in self.last_score.items()},
               'current_end':None,'current_points_from_stones':None,
               'physical_identity_verified':False}
        if write_stream:
            self._record_coverage(state)
            self.stream.write(json.dumps(state)+'\n')
            self.count+=1
            if self.count%25==0:self.stream.flush()
        return state

    def close(self):
        self.stream.flush()
        self.stream.close();self.score_stream.close()
        if self.geometry is not None and hasattr(self.geometry, 'close'):
            self.geometry.close()
        summary={'samples':self.count,'geometry_seconds':self.geometry_s,'ocr_seconds':self.ocr_s,
                 'geometry_skipped_frames':self.geometry_skipped_frames,
                 'geometry_schedule':self.config.get('geometry_schedule'),
                 'last_observed_totals':self.last_score,'new_calibration_fits':0,
                 'physical_trajectory_accuracy_measured':False}
        if self.geometry is not None:
            summary['geometry']=self.geometry.provenance()
            summary['new_calibration_fits']=getattr(self.geometry,'source_house_fit_attempts',0)
            if hasattr(self.geometry, 'native_fit_attempts'):
                summary['calibration_attempt_counts'] = {
                    'existing_receiving_house_fits': self.geometry.source_house_fit_attempts,
                    'native_receiving_marking_fits': self.geometry.native_fit_attempts,
                    'departure_boundary_initializations': self.geometry.boundary_attempts,
                    'departure_boundary_registration_checks': self.geometry.boundary_registration_checks,
                }
                summary['new_calibration_fits'] += self.geometry.native_fit_attempts + self.geometry.boundary_attempts
        if self.config.get('geometry_mode')=='explicit_source_calibration_v1':
            summary['calibration_coverage']=self.calibration_coverage
            summary['calibration_gaps']=self.calibration_gaps
            summary['manual_calibration']=True
            summary['calibration_bundle_sha256']=self.provenance['source_calibration_bundle_sha256']
        (self.output/'match-observation-summary.json').write_text(json.dumps(summary,indent=2))
        return summary
