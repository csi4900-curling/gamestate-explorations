"""Export angular-observability evidence using saved detector/receiver inputs.

No angular velocity is predicted here. Native detector crop dimensions and source
context are preserved so that missing handle detail is inspected, not assumed.
All model-selected moving observations remain available in the JSON index.
"""
import argparse
import json
from pathlib import Path

import cv2
import numpy as np

from prototype.detection_cache import digest
from prototype.post_throw_state import compact_events, write_json


def export(video, public_run, aggregate, motion_dir, event_ids, output, *, samples=5, context_scale=2.):
    public_run,output,motion_dir=map(Path,(public_run,output,motion_dir))
    if output.exists():raise ValueError('Preserve prior angular-observability evidence')
    if samples<2 or context_scale<1:raise ValueError('At least two samples and context scale >=1 required')
    protocol=json.loads((public_run/'protocol.json').read_text())
    source_hash=digest(video)
    if protocol['source_sha256']!=source_hash:raise ValueError('Source/run mismatch')
    manifest=json.loads((motion_dir/'manifest.json').read_text())
    if manifest['source_sha256']!=source_hash or manifest['observations_sha256']!=digest(public_run/'observations.jsonl'):
        raise ValueError('Source/motion observations mismatch')
    import ijson
    with Path(aggregate).open('rb') as stream:
        if next(ijson.items(stream,'context.source_sha256'),None)!=source_hash:
            raise ValueError('Source/aggregate mismatch')
    events=compact_events(aggregate);wanted=set(event_ids)
    if wanted-{e['candidate_id'] for e in events}:raise ValueError('Unknown event IDs')
    motion={}
    for p in ('left','right'):
        with np.load(motion_dir/(p+'.npz')) as a:
            motion[p]={(int(f),int(t)) for f,t,s in zip(a['frame_index'],a['track_id'],a['stationary']) if not s}
    selections=[];by_track={}
    for i,e in enumerate(events):
        if e['candidate_id'] not in wanted:continue
        receivers=[s for s in e['segments'] if s['role']=='receiving' and s['pixel_points']]
        selection={'event_id':e['candidate_id'],'observations':[],'physical_revolutions':None}
        selections.append(selection)
        if len(receivers)!=1:
            selection['status']='missing_or_ambiguous_receiver';continue
        s=receivers[0];p=s.get('rink_panel') or {'left_split':'left','right_split':'right'}[s['camera']]
        selection.update(panel=p,tracker_id=s['tracker_id'],status='angular_source_review_pending',
                         interval_s=[s['pixel_points'][0]['time_s'],events[i+1]['event_prediction']['crossing_time_s']
                                     if i+1<len(events) else protocol['source_interval_s'][1]])
        by_track.setdefault((p,s['tracker_id']),[]).append(selection)
    with (public_run/'observations.jsonl').open() as stream:
        for line in stream:
            row=json.loads(line)
            for point in row['tracked_observations']:
                panel='left' if point['point_normalized'][0]<.5 else 'right'
                key=(panel,point['track_id'])
                if key not in by_track or (row['frame_index'],point['track_id']) not in motion[panel]:continue
                for selection in by_track[key]:
                    if selection['interval_s'][0]<=row['time_s']<selection['interval_s'][1]:
                        selection['observations'].append({'frame_index':row['frame_index'],'time_s':row['time_s'],
                                                          'bbox_xyxy':point['bbox_xyxy'],'pixel':point['pixel']})
    output.mkdir(parents=True);cap=cv2.VideoCapture(str(video));all_crops=[]
    try:
        for selection in selections:
            rows=selection['observations']
            if not rows:selection['status']='no_model_moving_observations';continue
            indices=np.unique(np.rint(np.linspace(0,len(rows)-1,min(samples,len(rows)))).astype(int))
            selection['review_samples']=[]
            for j,index in enumerate(indices):
                row=rows[int(index)];frame=row['frame_index'];cap.set(cv2.CAP_PROP_POS_FRAMES,frame)
                ok,image=cap.read()
                if not ok or round(cap.get(cv2.CAP_PROP_POS_FRAMES))-1!=frame:raise ValueError('Source frame mismatch')
                x0,y0,x1,y1=row['bbox_xyxy'];cx,cy=(x0+x1)/2,(y0+y1)/2
                w,h=(x1-x0)*context_scale,(y1-y0)*context_scale
                bounds=[max(0,int(np.floor(cx-w/2))),max(0,int(np.floor(cy-h/2))),
                        min(image.shape[1],int(np.ceil(cx+w/2))),min(image.shape[0],int(np.ceil(cy+h/2)))]
                a,b,c,d=bounds;crop=image[b:d,a:c];name=f"{selection['event_id']}-{j}.png"
                if not cv2.imwrite(str(output/name),crop):raise IOError('Crop write failed')
                selection['review_samples'].append({**row,'crop':name,'crop_source_bounds':bounds,
                    'detector_box_size_px':[x1-x0,y1-y0], 'physical_orientation':None})
                all_crops.append((selection['event_id'],row['time_s'],crop,[x1-x0,y1-y0]))
    finally:cap.release()
    # Nearest-neighbour enlargement is only for review; it adds no source detail.
    from PIL import Image,ImageDraw
    sheet=Image.new('RGB',(samples*240,max(1,len(selections))*240),'white');draw=ImageDraw.Draw(sheet)
    for k,selection in enumerate(selections):
        for j,s in enumerate(selection.get('review_samples',[])):
            image=Image.open(output/s['crop']);image.thumbnail((220,190))
            # Enlarge while preserving aspect, displaying the native size above it.
            factor=min(220/image.width,190/image.height)
            image=image.resize((round(image.width*factor),round(image.height*factor)),Image.Resampling.NEAREST)
            sheet.paste(image,(j*240,k*240+45));w,h=s['detector_box_size_px']
            draw.text((j*240+3,k*240+3),f"{selection['event_id']} {s['time_s']:.1f}s",fill='black')
            draw.text((j*240+3,k*240+22),f"body box {w:.1f} x {h:.1f} px",fill='black')
    sheet.save(output/'contact-sheet.png')
    result={'development':True,'source_sha256':source_hash,'selection':{
        'event_ids':event_ids,'samples_per_event':samples,'context_scale':context_scale,
        'policy':'Equally spaced indices in the existing receiving-track observations classified moving by recording-level HMM.',
        'prediction_exposure':'Agent has seen previous pipeline predictions; this is feasibility inspection, not independent ground truth.'},
        'events':selections,'physical_revolutions':None,
        'limitations':['Tracker boxes do not identify handle landmarks or physical stone identity.',
                       'No physical angular velocity or revolution count follows from these crops alone.',
                       'Moving-state sampling is model dependent and may include tracker errors.'],
        'input_sha256':{'observations':digest(public_run/'observations.jsonl'),'aggregate':digest(aggregate),
                        'motion_manifest':digest(motion_dir/'manifest.json')},
        'code_sha256':digest(__file__)}
    write_json(output/'evidence.json',result)
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['video','public-run','aggregate','motion-dir','output']:parser.add_argument('--'+name,required=True)
    parser.add_argument('--events',nargs='+',required=True)
    a=parser.parse_args();export(a.video,a.public_run,a.aggregate,a.motion_dir,a.events,a.output)
