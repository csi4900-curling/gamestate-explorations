"""Receiving scene initialization using the unchanged existing cap detector.

No collision-specific timing, thresholds, landmarks, or physical motion model.
Stationary and delivered cap proposals are independent upstream point queries.
"""
import cv2

from prototype.stone_motion_fallback import stone_cap_candidates
from prototype.right_large_cap_proposals import right_large_cap_proposals


# Same observation budget as split_receiving_trajectory.complete_receiving.
RECEIVING_EVENT_BUDGET_S = 40.0


def receiving_episode_interval(aggregate, event, segment, source_end_s):
    start=min(p['time_s'] for p in segment['pixel_points'])
    observations=event['event_prediction'].get('observed_track_points', [])
    if not observations:
        raise ValueError('Receiving episode needs original event timing; cannot choose an end from collision footage')
    event_start=min(p['time_s'] for p in observations)
    boundaries=[(event_start+RECEIVING_EVENT_BUDGET_S,'existing_40_second_event_budget'),
                (source_end_s,'source_end'),(aggregate['source_interval_s'][1],'requested_source_end')]
    boundaries += [(t,'known_camera_cut') for t in segment.get('camera_cut_times_s',[]) if t>start]
    # Do not absorb another delivery into the same physical-stone episode.
    for other in aggregate['events']:
        if other['candidate_id']==event['candidate_id']:continue
        points=other.get('event_prediction',{}).get('observed_track_points',[])
        if points:
            t=min(p['time_s'] for p in points)
            if t>start:boundaries.append((t,'next_detected_delivery'))
    end,reason=min(boundaries)
    if end<=start:raise ValueError('No receiving episode after declared start')
    return [start,end], {'end_reason':reason,'event_start_s':event_start,
                         'budget_s':RECEIVING_EVENT_BUDGET_S,
                         'legacy_track_end_s':max(p['time_s'] for p in segment['pixel_points']),
                         'physical_stop_detected':False}


def receiving_scene_seeds(video, time_s, delivered_pixel, delivered_colour, *, detector="existing_right_caps"):
    if detector not in ("existing_right_caps", "legacy_body_filtered"):
        raise ValueError("Unknown scene seed detector")
    cap=cv2.VideoCapture(str(video))
    if not cap.isOpened():raise ValueError('Cannot decode receiving initialization')
    try:
        fps=cap.get(cv2.CAP_PROP_FPS);cap.set(cv2.CAP_PROP_POS_FRAMES,round(time_s*fps))
        ok,frame=cap.read()
        if not ok:raise ValueError('Missing receiving initialization frame')
        if round(cap.get(cv2.CAP_PROP_POS_FRAMES))-1!=round(time_s*fps):raise ValueError('Receiving initialization seek mismatch')
        height,width=frame.shape[:2]
        normalized=cv2.resize(frame,(640,360));crop=normalized[110:360,320:640]
        target=[delivered_pixel[0]*640/width,delivered_pixel[1]*360/height]
        seeds=[];proposals=[]
        broad=right_large_cap_proposals(normalized) if detector=='existing_right_caps' else None
        for colour in ('red','yellow'):
            detections=(broad[colour] if broad is not None else
                        stone_cap_candidates(crop,colour,allow_bright_body=True,allow_large_caps=True))
            for proposal in sorted(detections,key=lambda p:tuple(p['pixel'])):
                x,y=proposal['pixel'];bx,by,bw,bh=proposal['bbox']
                if broad is not None:
                    point=[x,y];box=[bx,by,bw,bh]
                else:
                    point=[320+x*.5,110+y*250/360];box=[320+bx*.5,110+by*250/360,bw*.5,bh*250/360]
                # An existing delivered seed inside this detector box is the same
                # initialization, not a second physical stone. No distance gate added.
                duplicate=(colour==delivered_colour and box[0]<=target[0]<=box[0]+box[2]
                           and box[1]<=target[1]<=box[1]+box[3])
                record={'colour':colour,'pixel_640x360':point,'bbox_640x360':box,
                        'overlaps_delivered_seed':duplicate,'detector_evidence':proposal}
                proposals.append(record)
                if not duplicate:
                    seeds.append({'name':f'scene_{colour}_{len(seeds):02d}',
                                  'pixel':[point[0]*width/640,point[1]*height/360],
                                  'colour':colour,'physical_identity_verified':False,
                                  'initialization':'existing cap detector, first receiving frame'})
        return seeds,{'frame_time_s':time_s,'detector':('right_large_cap_proposals.right_large_cap_proposals' if broad is not None else 'stone_motion_fallback.stone_cap_candidates'),
                      'thresholds_changed':False,'proposals':proposals,
                      'interpretation':'Cap proposals, not independently verified stone detections. Missing/occluded stones are not seeded.'}
    finally:cap.release()


def learned_scene_seeds(video, time_s, delivered_pixel, crop, detector):
    """Seed learned body boxes without interpreting their class as colour or identity.

    The existing event cap query remains the delivered-point anchor. A detection
    containing it is represented by that anchor, not assigned a new physical ID.
    Multiple containing boxes are recorded as ambiguous, not resolved by distance.
    """
    cap = cv2.VideoCapture(str(video))
    try:
        fps=cap.get(cv2.CAP_PROP_FPS);cap.set(cv2.CAP_PROP_POS_FRAMES,round(time_s*fps))
        ok,frame=cap.read()
        if not ok or round(cap.get(cv2.CAP_PROP_POS_FRAMES))-1!=round(time_s*fps):
            raise ValueError('Learned initialization source seek failed')
    finally:
        cap.release()
    predicted=detector.detect(frame)
    seeds=[];observations=[];overlapping=[]
    for index,p in enumerate(predicted['detections']):
        x,y=p['pixel'];x1,y1,x2,y2=p['bbox_xyxy']
        if not (crop[0]<=x<crop[2] and crop[1]<=y<crop[3]):continue
        overlap=x1<=delivered_pixel[0]<=x2 and y1<=delivered_pixel[1]<=y2
        observations.append({**p,'overlaps_event_cap_query':overlap})
        if overlap:
            overlapping.append(index)
            continue
        seeds.append({'name':f'scene_stone_{index:02d}', 'pixel':p['pixel'],
                      'colour':None,'physical_identity_verified':False,
                      'point_kind':'body_box_center', 'detector_confidence':p['confidence'],
                      'initialization':'Learned stone bounding-box centre; not a measured cap or contact point'})
    return seeds,{'frame_time_s':time_s,'detector':detector.provenance,
                  'detections':observations,'wall_seconds':predicted['wall_seconds'],
                  'event_query_support':'unique_box' if len(overlapping)==1 else 'ambiguous_boxes' if overlapping else 'no_box',
                  'overlapping_box_indices':overlapping,
                  'event_query_retained':True,'physical_identity_verified':False,
                  'interpretation':'Existing event cap anchor retained; additional learned body-box queries. Missing/occluded stones are not initialized.'}
