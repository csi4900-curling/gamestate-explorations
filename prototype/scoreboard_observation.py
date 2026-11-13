"""Read scoreboard totals from upstream OCR, retaining raw evidence and unknowns.

This is a layout parser, not a trained score model. It requires an observed TOTAL
header and configured team labels in the same frame. It does not infer a score
from throw counts, carry stale observations forward as current, or guess an end.
"""
import re
import time
import numpy as np
from prototype.score_grid import parse_end_cells


def parse_totals(texts, scores, boxes, team_labels):
    tokens=[]
    for text, score, box in zip(texts, scores, boxes):
        points=np.asarray(box,dtype=float)
        tokens.append({'text':text,'normalized':re.sub('[^A-Z0-9]','',text.upper()),
                       'confidence':float(score),'box':points.tolist(),
                       'bounds':[float(points[:,0].min()),float(points[:,1].min()),
                                 float(points[:,0].max()),float(points[:,1].max())]})
    headers=[t for t in tokens if t['normalized']=='TOTAL']
    result={team:{'value':None,'status':'unreadable_or_ambiguous','evidence':[]} for team in team_labels}
    for team in team_labels:
        candidates=[]
        for header in headers:
            hx0,hy0,hx1,hy1=header['bounds']
            labels=[t for t in tokens if t['normalized']==team.upper() and t['bounds'][2]<hx0 and t['bounds'][1]>hy0]
            for label in labels:
                lx0,ly0,lx1,ly1=label['bounds']
                for digit in tokens:
                    dx0,dy0,dx1,dy1=digit['bounds']
                    # Infer column/row from observed text extents, not fixed pixels.
                    if digit['normalized'].isdigit() and hx0 <= (dx0+dx1)/2 <= hx1 and ly0 <= (dy0+dy1)/2 <= ly1:
                        candidates.append({'value':int(digit['normalized']),
                                           'evidence':[header,label,digit]})
        if len(candidates)==1:
            result[team]={**candidates[0],'status':'ocr_observed_unverified',
                          'confidence':min(t['confidence'] for t in candidates[0]['evidence']),
                          'confidence_calibrated':False}
        elif candidates:
            result[team]['candidates']=candidates
    grid = parse_end_cells(tokens, team_labels)
    return {'totals':result,'current_end':None,'current_end_status':'physical_end_not_established',
            'displayed_end':grid['current_end'],
            'displayed_end_status':grid['current_end_status'],
            'displayed_end_evidence':grid['current_end_evidence'],
            'end_score_cells':grid['end_score_cells'],
            'displayed_end_interpretation':grid['end_interpretation'],
            'tokens':tokens,'method':'TOTAL column plus configured team row text overlap',
            'physical_board_score':None,'physical_board_score_status':'requires team identity and complete stone positions'}


class ScoreboardObserver:
    def __init__(self, *, team_labels, model_dir, crop_normalized=(0,0,1,1), threads=2):
        from rapidocr import RapidOCR
        self.team_labels=tuple(team_labels)
        if len(self.team_labels)!=2 or len(set(self.team_labels))!=2:
            raise ValueError('Two distinct scoreboard team labels required')
        x0,y0,x1,y1=crop_normalized
        if not (0<=x0<x1<=1 and 0<=y0<y1<=1):raise ValueError('Invalid OCR crop')
        self.crop=tuple(crop_normalized)
        self.engine=RapidOCR(params={'EngineConfig.onnxruntime.intra_op_num_threads':threads,
                                    'EngineConfig.onnxruntime.inter_op_num_threads':1,
                                    'Global.model_root_dir':str(model_dir)})

    def observe(self,frame,time_s):
        started=time.perf_counter();h,w=frame.shape[:2]
        x0,y0,x1,y1=[round(v*s) for v,s in zip(self.crop,(w,h,w,h))]
        result=self.engine(frame[y0:y1,x0:x1])
        if result.boxes is None:
            texts,scores,boxes=[],[],[]
        else:
            texts,scores=result.txts,result.scores
            boxes=np.asarray(result.boxes)+np.asarray([x0,y0])
        return {'time_s':time_s,'crop_normalized':self.crop,
                **parse_totals(texts,scores,boxes,self.team_labels),
                'wall_seconds':time.perf_counter()-started}


def scan(video, config_path, output, *, start=0., end=None):
    """Resumable full-recording OCR stage, shared by the match orchestrator.

    Writes observations incrementally. Existing data may only resume under the
    same source, parser, OCR weights and configuration hashes.
    """
    import cv2
    import importlib.metadata
    import json
    from pathlib import Path
    from prototype.match_observation import sha
    video=Path(video).resolve();config_path=Path(config_path).resolve();output=Path(output)
    cfg=json.loads(config_path.read_text())
    interval=float(cfg['score_sample_interval_s'])
    if not np.isfinite(interval) or interval<=0:raise ValueError('Positive OCR sample interval required')
    model_dir=(config_path.parent/cfg['ocr_model_dir']).resolve()
    observer=ScoreboardObserver(team_labels=cfg['scoreboard_team_labels'],model_dir=model_dir,
                               crop_normalized=cfg['scoreboard_crop_normalized'])
    cap=cv2.VideoCapture(str(video));fps=cap.get(cv2.CAP_PROP_FPS);duration=cap.get(cv2.CAP_PROP_FRAME_COUNT)/fps
    end=duration if end is None else end
    if not 0<=start<end<=duration:raise ValueError('Invalid score scan interval')
    contract={'source_sha256':sha(video),'config_sha256':sha(config_path),'code_sha256':sha(__file__),
              'grid_parser_sha256':sha(Path(__file__).with_name('score_grid.py')),
              'rapidocr':importlib.metadata.version('rapidocr'),'onnxruntime':importlib.metadata.version('onnxruntime'),
              'model_sha256':{p.name:sha(p) for p in sorted(model_dir.glob('*.onnx'))},
              'interval_s':[start,end],'sample_interval_s':interval,'input_resolution':[cap.get(3),cap.get(4)],
              'reference_labels_used':False,'development':True}
    output.mkdir(parents=True,exist_ok=True);protocol=output/'protocol.json';data=output/'observations.jsonl'
    previous=[]
    if protocol.exists():
        if json.loads(protocol.read_text())!=contract:raise ValueError('Cannot resume changed scoreboard stage')
        previous=[json.loads(line) for line in data.read_text().splitlines()] if data.exists() else []
    else:
        if data.exists():raise ValueError('Unversioned score output exists')
        protocol.write_text(json.dumps(contract,indent=2));(output/'parser.py').write_bytes(Path(__file__).read_bytes())
        (output/'config.json').write_bytes(config_path.read_bytes())
    count=len(previous);started=time.perf_counter();ocr_seconds=sum(r['wall_seconds'] for r in previous)
    next_time=start+count*interval
    try:
        with data.open('a') as stream:
            while next_time<end:
                frame_index=round(next_time*fps);cap.set(cv2.CAP_PROP_POS_FRAMES,frame_index)
                ok,frame=cap.read()
                if not ok or round(cap.get(cv2.CAP_PROP_POS_FRAMES))-1!=frame_index:
                    raise RuntimeError(f'Cannot read score source frame {frame_index}')
                row=observer.observe(frame,frame_index/fps);row['frame_index']=frame_index
                stream.write(json.dumps(row)+'\n');stream.flush();ocr_seconds+=row['wall_seconds'];count+=1
                if count%25==0:print(json.dumps({'score_samples':count,'source_time_s':next_time,'wall_seconds_this_attempt':time.perf_counter()-started}),flush=True)
                next_time=start+count*interval
    finally:cap.release()
    summary={'status':'complete_ocr_stage_only','samples':count,'ocr_seconds':ocr_seconds,
             'wall_seconds_this_attempt':time.perf_counter()-started,'resumed_samples':len(previous),
             'score_accuracy_validated':False,'current_end_extraction_implemented':False,
             'displayed_end_marker_extraction_implemented':True}
    (output/'summary.json').write_text(json.dumps(summary,indent=2));return summary


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description='Shared scoreboard stage: learned OCR with explicit unknown totals')
    parser.add_argument('--video',required=True);parser.add_argument('--config',required=True)
    parser.add_argument('--output',required=True)
    args=parser.parse_args();print(scan(args.video,args.config,args.output))
