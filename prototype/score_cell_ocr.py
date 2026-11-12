"""Development OCR ablation: recognize cells in a grid estimated from OCR text.

Reuses RapidOCR recognition. No fixed scoreboard coordinates, end count or new
confidence cutoff. Returned text is raw evidence; blank/occluded cells may produce
hallucinated digits and must not automatically become game state.
"""
import argparse
import hashlib
import json
import time
from pathlib import Path
import numpy as np


def estimate_cells(tokens, teams):
    anchors=[t for t in tokens if t['normalized']=='END']
    if len(anchors)!=1:return {'status':'no_unique_END_header','cells':[]}
    ax0,ay0,ax1,ay1=anchors[0]['bounds'];headers=[]
    for token in tokens:
        text=token['text'].strip();x0,y0,x1,y1=token['bounds']
        if text.isdecimal() and int(text)>0 and x0>ax1 and ay0<=(y0+y1)/2<=ay1:
            headers.append((int(text),(x0+x1)/2))
    headers.sort(key=lambda h:h[1])
    supported=[(value,x) for i,(value,x) in enumerate(headers)
               if (i>0 and headers[i-1][0]==value-1) or (i+1<len(headers) and headers[i+1][0]==value+1)]
    if len(supported)<2 or len(set(v for v,x in supported))!=len(supported):return {'status':'insufficient_unique_header_labels','cells':[]}
    values=np.asarray([v for v,x in supported]);positions=np.asarray([x for v,x in supported])
    pitch,origin=np.polyfit(values,positions,1)
    if pitch<=0:return {'status':'nonpositive_grid_pitch','cells':[]}
    cells=[]
    for team in teams:
        labels=[t for t in tokens if t['normalized']==team.upper() and t['bounds'][2]<positions.min() and t['bounds'][1]>ay1]
        if len(labels)!=1:continue
        _,y0,_,y1=labels[0]['bounds']
        for value in range(1,int(values.max())+1):
            x=origin+pitch*value
            cells.append({'team':team,'end_column':value,'crop_xyxy':[round(x-pitch/2),round(y0),round(x+pitch/2),round(y1)]})
    return {'status':'estimated_from_ocr','header_evidence':supported,'pitch_px':float(pitch),
            'origin_px':float(origin),'header_fit_residuals_px':(positions-(origin+pitch*values)).tolist(),'cells':cells}


def probe(video, observations, output, teams, times, model_dir):
    import cv2
    from rapidocr import RapidOCR
    import importlib.metadata
    from prototype.detection_cache import digest
    video,observations,output=map(Path,(video,observations,output))
    if output.exists():raise ValueError('Preserve earlier probe')
    protocol_path=observations.parent/'protocol.json'
    protocol=json.loads(protocol_path.read_text())
    source_sha=digest(video)
    if source_sha!=protocol['source_sha256']:raise ValueError('OCR observations and video source differ')
    output.mkdir(parents=True)
    engine=RapidOCR(params={'Global.model_root_dir':str(model_dir),'EngineConfig.onnxruntime.intra_op_num_threads':2,'EngineConfig.onnxruntime.inter_op_num_threads':1})
    cap=cv2.VideoCapture(str(video));fps=cap.get(cv2.CAP_PROP_FPS);rows=[];requested=set(times)
    try:
        for line in observations.open():
            row=json.loads(line)
            if row['time_s'] not in requested:continue
            grid=estimate_cells(row['tokens'],teams);frame_index=row['frame_index']
            cap.set(cv2.CAP_PROP_POS_FRAMES,frame_index);ok,frame=cap.read()
            if not ok or round(cap.get(cv2.CAP_PROP_POS_FRAMES))-1!=frame_index:raise ValueError('Cannot read exact source frame')
            started=time.perf_counter()
            for cell in grid['cells']:
                x0,y0,x1,y1=cell['crop_xyxy']
                if not 0<=x0<x1<=frame.shape[1] or not 0<=y0<y1<=frame.shape[0]:
                    cell['status']='invalid_crop';continue
                crop=frame[y0:y1,x0:x1];read=engine(crop,use_det=False,use_cls=False,use_rec=True)
                cell['text']=list(read.txts) if read.txts is not None else []
                cell['scores']=[float(s) for s in read.scores] if read.scores is not None else []
                cell['status']='raw_unverified';name=f'{frame_index}-{cell["team"]}-{cell["end_column"]}.png';cv2.imwrite(str(output/name),crop);cell['image']=name
            rows.append({'time_s':row['time_s'],'frame_index':frame_index,'grid':grid,'wall_seconds':time.perf_counter()-started})
    finally:cap.release()
    data={'development':True,'method':'RapidOCR recognizer on OCR-inferred end cells; programmed grid estimation',
          'source_sha256':source_sha,'input_protocol_sha256':digest(protocol_path),
          'model_sha256':{p.name:digest(p) for p in Path(model_dir).glob('*.onnx')},
          'rapidocr':importlib.metadata.version('rapidocr'),'input_observations_sha256':hashlib.sha256(observations.read_bytes()).hexdigest(),
          'code_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'requested_times':sorted(times),
          'current_state_predictions':False,'observations':rows}
    (output/'result.json').write_text(json.dumps(data,indent=2)+'\n');(output/'code.py').write_bytes(Path(__file__).read_bytes());return data


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--video',required=True);p.add_argument('--observations',required=True);p.add_argument('--output',required=True);p.add_argument('--teams',nargs=2,required=True);p.add_argument('--times',nargs='+',type=float,required=True);p.add_argument('--model-dir',required=True)
    a=p.parse_args();probe(a.video,a.observations,a.output,a.teams,a.times,a.model_dir)
