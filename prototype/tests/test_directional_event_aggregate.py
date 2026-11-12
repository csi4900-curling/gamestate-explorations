import json
from prototype.detection_cache import digest
from prototype.directional_event_aggregate import build


def test_receiving_primary_links_to_earlier_opposite_panel_departure(tmp_path):
    video=tmp_path/'fixture.bin';video.write_bytes(b'source identity fixture; no video decoding in bridge')
    run=tmp_path/'run';run.mkdir();observations=[];boards=[]
    for t in range(6):
        raw={'time_s':t,'frame_index':t,'tracked_observations':[]}
        state={'time_s':t,'frame_index':t,'boards':{p:{'stones':[],
            'registration':{'status':'fixture'},'homography_normalized_pixels_to_local_metres':[[1,0,0],[0,1,0],[0,0,1]]}
            for p in ['left','right']}}
        if t in [1,2,4,5]:
            panel='right' if t<3 else 'left';track=2 if t<3 else 1
            pixel=[500,200+20*t] if t<3 else [100,20+10*(t-4)]
            xy=[0,5+t] if t<3 else [0,t-14]
            raw['tracked_observations'].append({'track_id':track,'point_normalized':[pixel[0]/640,pixel[1]/360],
                'pixel':pixel,'bbox_xyxy':[0,0,1,1],'confidence':.9})
            state['boards'][panel]['stones'].append({'tracker_id':track,'pixel':pixel,'confidence':.9,
                'ice_plane_local_m':xy,'height_adjusted_local_m':xy})
        observations.append(raw);boards.append(state)
    event={'id':'A','track_id':1,'crossing_time_s':4.5,'crossing_point_normalized':[100/640,25/360],
        'observations':[{'time_s':t,'pixel':observations[t]['tracked_observations'][0]['pixel']} for t in [4,5]]}
    (run/'events.json').write_text(json.dumps({'source_sha256':digest(video),'source_size_px':[640,360],
        'source_interval_s':[0,6],'sample_step_frames':1,'events':[event]}))
    for name,rows in [('observations.jsonl',observations),('match-observations.jsonl',boards)]:
        (run/name).write_text(''.join(json.dumps(r)+'\n' for r in rows))
    result=build(video,run,tmp_path/'aggregate.json',hog_y_by_panel={'left':-6.401,'right':6.401})
    event=result['events'][0]
    assert [(s['camera'],s['role']) for s in event['segments']]==[('left_split','receiving'),('right_split','departure')]
    link=event['cross_view_links'][0]
    assert link['departure_segment']=='A:departure:2'
    assert link['receiving_segment']=='A:primary' and link['gap_s']==2
    assert not link['physical_identity_verified']
