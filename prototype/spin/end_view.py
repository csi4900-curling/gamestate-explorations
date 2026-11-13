"""Source evidence at the end of an analyzed receiving episode, not a settled board."""
from pathlib import Path
import math
import json
import copy

import cv2


def export_end_views(events, video, output, *, stone_detector=None, observation_run=None, stone_colour_model=None):
    """Keep both broadcast panels; never infer board identity from tracker endpoints."""
    output = Path(output)
    rows = []
    cap = cv2.VideoCapture(str(video))
    try:
        fps = cap.get(cv2.CAP_PROP_FPS)
        saved = {}
        if observation_run is not None and math.isfinite(fps) and fps > 0:
            wanted = {round(s['times_s'][-1]*fps) for e in events for s in e['segments']
                      if s.get('role') == 'receiving' and s.get('status') == 'tracked' and s.get('times_s')}
            with (Path(observation_run)/'match-observations.jsonl').open() as stream:
                for line in stream:
                    observation = json.loads(line)
                    if observation['frame_index'] in wanted:
                        if observation['frame_index'] in saved:
                            raise ValueError('Duplicate board snapshot frame')
                        if abs(observation['time_s']-observation['frame_index']/fps) > 1e-6:
                            raise ValueError('Board snapshot frame/time mismatch')
                        saved[observation['frame_index']] = observation
        for index, event in enumerate(events):
            row = {'candidate_id': event['candidate_id'], 'status': 'unavailable',
                   'settled': None, 'physical_end_identity': 'unknown',
                   'basis': 'Last analyzed receiving frame; settlement is not detected.'}
            rows.append(row)
            segments = [s for s in event['segments'] if s.get('role') == 'receiving'
                        and s.get('status') == 'tracked' and s.get('times_s')]
            if not segments:
                row['reason'] = 'No analyzed receiving frames'
                continue
            if not cap.isOpened() or not math.isfinite(fps) or fps <= 0:
                row['reason'] = 'Source video cannot be decoded'
                continue
            segment = max(segments, key=lambda s: s['times_s'][-1])
            requested = segment['times_s'][-1]
            frame_index = round(requested * fps)
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
            ok, frame = cap.read()
            actual_index = round(cap.get(cv2.CAP_PROP_POS_FRAMES)) - 1
            if not ok or actual_index != frame_index:
                row['reason'] = 'Requested source frame could not be decoded exactly'
                continue
            relative = f'end-views/event-{index:04d}.png'
            (output / 'end-views').mkdir(exist_ok=True, parents=True)
            if not cv2.imwrite(str(output / relative), frame):
                row['reason'] = 'Source snapshot could not be saved'
                continue
            learned=stone_detector.detect(frame) if stone_detector is not None else None
            if stone_colour_model is not None and learned is not None:
                predictions=stone_colour_model.classify(frame,learned['detections'])
                row['colour_observations']={'provenance':stone_colour_model.provenance,'predictions':predictions,
                    'scope':'Exact snapshot source crops; colour ranking is not individual-stone, team or identity verification'}
                learned={**learned,'detections':[{**d,'colour_evidence':predictions[i]} for i,d in enumerate(learned['detections'])]}
            row['board']=project_board(frame, segment, actual_index / fps, learned=learned)
            if learned is not None:
                row['source_detections']=learned
                row['detector_provenance']=stone_detector.provenance
            annotated = frame.copy()
            if learned is not None:
                for detection_index,detection in enumerate(learned['detections']):
                    x1,y1,x2,y2=map(round,detection['bbox_xyxy'])
                    cv2.rectangle(annotated,(x1,y1),(x2,y2),(255,180,0),1)
                    colour=(detection.get('colour_evidence') or {}).get('prediction')
                    if colour is not None:
                        cv2.putText(annotated,f'D{detection_index}: {colour}?',(x1,max(12,y1-5)),cv2.FONT_HERSHEY_SIMPLEX,.5,(255,180,0),1,cv2.LINE_AA)
            for stone in row['board']['stones']:
                x, y = stone['pixel_640x360']
                point = (round(x * frame.shape[1] / 640), round(y * frame.shape[0] / 360))
                cv2.circle(annotated, point, 7, (255, 180, 0), 1)
                cv2.putText(annotated, str(stone['observation_id']), (point[0]+8, point[1]-8),
                            cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 180, 0), 1, cv2.LINE_AA)
            annotated_path = f'end-views/event-{index:04d}-proposals.png'
            if cv2.imwrite(str(output / annotated_path), annotated):
                row['annotated_image'] = annotated_path
            row.update(status='observed', image=relative, frame_index=actual_index,
                       time_s=actual_index / fps, requested_time_s=requested,
                       segment_id=segment['segment_id'], source_fps=fps,
                       width=frame.shape[1], height=frame.shape[0])
            observation = saved.get(actual_index)
            row['both_panel_observations'] = ({
                'status': 'observed', 'time_s': observation['time_s'],
                'frame_index': actual_index, 'boards': observation['boards'],
                'source': 'Exact-frame saved public match observations; no new inference',
                'settled': None, 'physical_end_identity_verified': False,
                'score_observation': observation.get('score_observation'),
            } if observation is not None else {
                'status': 'unavailable', 'reason': 'No exact-frame saved board observation; no nearby frame substituted'})
            if stone_colour_model is not None and observation is not None:
                both=row['both_panel_observations']
                both['boards']=copy.deepcopy(both['boards'])
                both['source']='Exact-frame saved positions; new colour predictions on their original source boxes'
                both['colour_provenance']=stone_colour_model.provenance
                for panel,board in both['boards'].items():
                    predictions=stone_colour_model.classify(frame,board['stones'])
                    for stone,prediction in zip(board['stones'],predictions):
                        stone['colour_evidence']=prediction

    finally:
        cap.release()
    return rows


def project_board(frame, segment, time_s, *, learned=None):
    """Fresh existing colour proposals, using the saved same-frame registration.

    This is an incomplete board observation, not tracked physical identities.
    No geometry is fitted and no tracker visibility mask suppresses these proposals.
    """
    import numpy as np
    from .projection import transported_reference_camera, localize, feature_heights
    from prototype.right_large_cap_proposals import right_large_cap_proposals
    board = {'status': 'unavailable', 'stones': [], 'physical_accuracy_validated': False,
             'complete_board': False, 'score': None, 'time_s': time_s,
             'method': 'Existing right_large_cap_proposals defaults; separate raw and conditional height-corrected projections',
             'coordinate_system': 'Receiving camera-local metres; tee (0,0), +y toward foreground/hog',
             'new_calibration_fits': 0}
    if segment.get('camera') not in ('left_split', 'right_split') or (learned is None and segment.get('camera') != 'right_split'):
        board['reason'] = 'Existing receiving-board detector supports right_split only'
        return board
    panel_crop = (0,0,320,360) if segment['camera']=='left_split' else (320,0,640,360)
    board['coordinate_system'] = 'Receiving camera-local metres; saved calibration axes, tee (0,0)'
    board['camera'] = segment['camera']
    projection = segment.get('projection') or {}
    heights = feature_heights(projection.get('feature_heights_m'))
    board['feature_heights_m'] = heights
    samples = [s for s in projection.get('samples', []) if abs(s['time_s'] - time_s) < 1e-6]
    if not samples or not projection.get('anchor_homography'):
        board['reason'] = 'No geometry at the snapshot timestamp'
        return board
    registration = samples[0].get('registration', {})
    status = registration.get('status')
    if status not in ('existing_anchor_frame', 'image_registered_house_projection'):
        board['reason'] = 'Snapshot geometry unavailable: ' + str(status)
        return board
    try:
        A = np.asarray(registration['reference_to_current'] if status != 'existing_anchor_frame' else np.eye(3), float)
        H = np.asarray(projection['anchor_homography'], float) @ np.linalg.inv(A)
        prior = transported_reference_camera(np.asarray(projection['anchor_homography'], float), H, panel_crop)
        proposals = right_large_cap_proposals(cv2.resize(frame, (640, 360))) if learned is None else {'unknown':[]}
        kind='cap_with_body_support'
        if learned is not None:
            kind='body_box_center'
            board['method']=f"Learned stone body-box centres; conditional {heights['body_box_center']}m body-centre height, not measured contact points. Colour and identity unknown."
            for detection in learned['detections']:
                xy=np.array(detection['pixel'])*[640/frame.shape[1],360/frame.shape[0]]
                if panel_crop[0]<=xy[0]<panel_crop[2] and panel_crop[1]<=xy[1]<panel_crop[3]:
                    proposals['unknown'].append({'pixel':xy.tolist(),'confidence':detection['confidence'],'colour_evidence':detection.get('colour_evidence')})
        for colour, candidates in proposals.items():
            for candidate in candidates:
                q = H @ np.array([*candidate['pixel'], 1.])
                xy = (q[:2] / q[2]).tolist() if abs(q[2]) > 1e-12 else None
                if xy is not None and not np.isfinite(xy).all():
                    xy = None
                adjusted, diagnostic = localize(H, candidate['pixel'], panel_crop, kind, camera_prior=prior, heights_m=heights) if prior is not None else (None, {'status':'unavailable', 'reason':'Reference camera cannot support height correction'})
                board['stones'].append({'observation_id': len(board['stones']) + 1,
                                        'colour': None if colour=='unknown' else colour, 'point_kind':kind, 'confidence':candidate.get('confidence'), 'pixel_640x360': candidate['pixel'],
                                        'position_m': xy, 'raw_position_m': xy,
                                        'height_adjusted_position_m': adjusted.tolist() if adjusted is not None else None,
                                        'height_adjustment': diagnostic, 'physical_identity': None, 'colour_evidence':candidate.get('colour_evidence')})
        board.update(status='proposals', registration_status=status)
    except (ValueError, KeyError, np.linalg.LinAlgError) as exc:
        board['reason'] = 'Saved geometry invalid: ' + str(exc)
    return board
