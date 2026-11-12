"""Learn per-recording apparent motion states using upstream Gaussian HMMs.

Apparent motion is in detected body-widths/second, not physical velocity. Tracks
and visibility gaps remain separate sequences. The low-motion state is a
stationary hypothesis; neither posterior nor state label certifies settlement.
"""
import argparse
import json
import math
from pathlib import Path
import time

import numpy as np
from prototype.detection_cache import digest


def sequences(rows, sample_step_frames):
    active = {}; finished = []
    for row in rows:
        present = set()
        for point in row['tracked_observations']:
            panel = 'left' if point['point_normalized'][0] < .5 else 'right'
            key = (panel, point['track_id']); present.add(key)
            sequence = active.get(key)
            if sequence is not None and row['frame_index'] != sequence['last_frame']+sample_step_frames:
                if sequence['samples']: finished.append(sequence)
                sequence = None
            if sequence is None:
                sequence = dict(panel=panel, track_id=point['track_id'], samples=[])
                active[key] = sequence
            if 'last_time' in sequence:
                dt = row['time_s']-sequence['last_time']
                if dt <= 0: raise ValueError('Non-increasing source times')
                width = point['bbox_xyxy'][2]-point['bbox_xyxy'][0]
                scale = (sequence['last_width']+width)/2
                if scale <= 0: raise ValueError('Invalid observed body width')
                speed = math.dist(sequence['last_pixel'],point['pixel'])/(dt*scale)
                sequence['samples'].append((row['frame_index'],row['time_s'],speed))
            sequence.update(last_time=row['time_s'],last_frame=row['frame_index'],last_pixel=point['pixel'],
                            last_width=point['bbox_xyxy'][2]-point['bbox_xyxy'][0])
        for key in list(active):
            if key not in present:
                if active[key]['samples']: finished.append(active[key])
                del active[key]
    finished.extend(s for s in active.values() if s['samples'])
    return finished


def fit_panel(items, *, n_iter=100, random_state=0):
    from hmmlearn.hmm import GaussianHMM
    lengths = [len(s['samples']) for s in items]
    motion = np.array([p[2] for s in items for p in s['samples']],float)
    if len(motion) < 2 or len(np.unique(motion)) < 2:
        raise ValueError('Motion states not identifiable from constant/insufficient data')
    features = np.log1p(motion).reshape(-1,1)
    model = GaussianHMM(n_components=2,covariance_type='diag',n_iter=n_iter,
                        random_state=random_state,implementation='scaling')
    started = time.perf_counter();model.fit(features,lengths)
    states = model.predict(features,lengths);posterior=model.predict_proba(features,lengths)
    stationary = int(np.argmin(model.means_[:,0]))
    samples=[];offset=0
    for sequence in items:
        for frame,t,speed in sequence['samples']:
            samples.append((frame,t,sequence['track_id'],speed,int(states[offset]==stationary),
                            float(posterior[offset,stationary])))
            offset+=1
    history=list(model.monitor_.history)
    return samples,{
        'backend':'hmmlearn.hmm.GaussianHMM','settings':model.get_params(),
        'feature':'log1p(apparent body-widths per second), from observed box centres only',
        'means_log_motion':model.means_.tolist(),'covariances':model.covars_.tolist(),
        'transition_matrix':model.transmat_.tolist(),'start_probabilities':model.startprob_.tolist(),
        'stationary_state':stationary,'sequences':len(items),'motion_samples':len(motion),
        'iterations':model.monitor_.iter,'iteration_budget_reached':model.monitor_.iter==n_iter,
        'last_log_likelihood_gain':history[-1]-history[-2] if len(history)>1 else None,
        'fit_decode_wall_s':time.perf_counter()-started,
        'probability_semantics':'Model posterior, not calibrated probability of true physical settlement.',
        'assumptions':['Two apparent-motion populations can represent stationary/moving tracks.',
                       'Raw image motion can include camera motion; no new camera compensation is claimed.',
                       'Offline fitting and Viterbi decoding use later observations.'],
    }


def run(public_run, output, *, n_iter=100, random_state=0):
    import hmmlearn, sklearn
    public_run,output=Path(public_run),Path(output)
    if output.exists():raise ValueError('Preserve existing motion fit')
    protocol=json.loads((public_run/'protocol.json').read_text())
    source=public_run/'observations.jsonl';before=digest(source)
    with source.open() as stream:
        tracks=sequences((json.loads(line) for line in stream),protocol['sample_step_frames'])
    output.mkdir(parents=True);results={}
    (output/'stone_motion.py').write_bytes(Path(__file__).read_bytes())
    (output/'plan.json').write_text(json.dumps({
        'source_sha256':protocol['source_sha256'],'observations_sha256':before,
        'n_components':2,'n_iter':n_iter,'random_state':random_state,
        'scope':'Development apparent-motion fit; no hand-selected per-throw velocity cutoff.'},indent=2)+'\n')
    for panel in ['left','right']:
        items=[s for s in tracks if s['panel']==panel]
        speeds=[p[2] for s in items for p in s['samples']]
        if len(speeds)<2 or len(set(speeds))<2:
            rows=[]
            info={'status':'unidentifiable','reason':'Constant or insufficient observed motion; no two-population fit.',
                  'input_motion_samples':len(speeds),'motion_samples':0,'iterations':0,'fit_decode_wall_s':0.,
                  'stationary_hypothesis':None,'posterior_stationary':None}
        else:
            rows,info=fit_panel(items,n_iter=n_iter,random_state=random_state)
            info['status']='fitted'
        data=np.asarray(rows,float).reshape(-1,6)
        np.savez_compressed(output/(panel+'.npz'),frame_index=data[:,0].astype(np.int64),time_s=data[:,1],
                            track_id=data[:,2].astype(np.int64),apparent_speed=data[:,3],
                            stationary=data[:,4].astype(bool),posterior_stationary=data[:,5])
        results[panel]=info
        print(panel,info['motion_samples'],'samples;',info['iterations'],'fit iterations',flush=True)
    if before!=digest(source):raise ValueError('Observation source changed during fitting')
    manifest={'development':True,'source_sha256':protocol['source_sha256'],'observations_sha256':before,
              'protocol_sha256':digest(public_run/'protocol.json'),'adapter_sha256':digest(__file__),
              'hmmlearn':hmmlearn.__version__,'sklearn':sklearn.__version__,'panels':results,
              'scope':'Apparent-motion hypotheses only; no stone identity, settled-board or score validation.'}
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2,allow_nan=False)+'\n')
    return manifest


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--public-run',required=True)
    p.add_argument('--output',required=True);p.add_argument('--n-iter',type=int,default=100)
    a=p.parse_args();run(a.public_run,a.output,n_iter=a.n_iter)
