"""Frozen-seed temporal sampling experiment against a saved CoTracker result.

Agreement with the baseline is not physical accuracy. The source-reviewed
identity failures of the baseline remain failures, not targets to reproduce.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import time
import numpy as np


def tracking_metadata(baseline):
    """Only immutable source/seed metadata, never baseline-derived measurements."""
    keys=['candidate_id','segment_id','interval_s','fps','crop_px','point_names',
          'point_kinds','seed_provenance']
    return {**{key:baseline[key] for key in keys if key in baseline},
            'schema_version':'temporal-sampling-component-experiment-v1',
            'status':'development_component_only',
            'physical_revolutions':None,'physical_identity_verified':False,
            'projection':None,'reconstruction':None,'masked_evaluation':None}


def component_result(raw):
    """Normalize the initial experiment writer without retaining stale analyses."""
    times=np.asarray(raw['times_s'],float)
    indices=np.asarray(raw['frame_indices'])
    tracks=np.asarray(raw['tracks_px'],float)
    visible=np.asarray(raw['point_visible'])
    count=len(times);queries=len(raw['point_names'])
    if count<2 or not np.all(np.diff(times)>0) or not np.isfinite(times).all():
        raise ValueError('Strict source timestamps required')
    if indices.shape!=(count,) or not np.all(np.diff(indices)==raw['sampling_experiment']['frame_step']):
        raise ValueError('Sampling indices differ from recorded experiment')
    if tracks.shape!=(count,queries,2) or visible.shape!=(count,queries):
        raise ValueError('Tracking arrays differ from sampled frames or queries')
    if raw['model']['native_frame_count']!=count:
        raise ValueError('Model frame count differs from saved predictions')
    if raw['model']['checkpoint_sha256']!=raw['sampling_experiment']['model_sha256']:
        raise ValueError('Experiment/model weights differ')
    return {**tracking_metadata(raw),**{key:raw[key] for key in [
        'times_s','frame_indices','tracks_px','point_visible','model',
        'sampling_experiment','provenance']}}


def normalize_saved_result(source, output):
    import hashlib
    source,output=Path(source),Path(output)
    if output.exists():raise ValueError('Preserve previous normalized result')
    raw=json.loads(source.read_text());result=component_result(raw)
    result['normalization_provenance']={
        'raw_result_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
        'normalizer_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'predictions_modified':False,'reason':'Remove inherited baseline analyses; preserve experiment predictions and timings'}
    output.write_text(json.dumps(result,indent=2))
    return result


def run(baseline, video, checkpoint, output, frame_step, adapter):
    spec=importlib.util.spec_from_file_location('frozen_point_adapter',adapter)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    baseline,video,checkpoint,output=map(Path,(baseline,video,checkpoint,output))
    if output.exists():raise ValueError('Preserve previous sampling experiment')
    r=json.loads(baseline.read_text())
    if module.digest(video)!=r['provenance']['source_sha256'] or module.digest(checkpoint)!=r['model']['checkpoint_sha256']:
        raise ValueError('Source or model differs')
    if module.decoder_identity()!=r['provenance']['decoded_input']['decoder']:
        raise ValueError('Decoder differs')
    if r['model']['device']!='cpu' or r['model']['mode']!='online':
        raise ValueError('This comparison requires the recorded online CPU baseline')
    output.mkdir(parents=True)
    plan={'baseline_sha256':module.digest(baseline),'source_sha256':module.digest(video),
          'model_sha256':module.digest(checkpoint),'adapter_sha256':module.digest(adapter),
          'experiment_code_sha256':module.digest(__file__),'frame_step':frame_step,
          'development':True,'public_pipeline_evaluated':False,
          'acceptance':'Compare common-frame coordinates, visibility, source-reviewed identity, and actual runtime before any promotion. No interpolation or corrective association.',
          'interval_s':r['interval_s'],'baseline_model':r['model']}
    (output/'plan.json').write_text(json.dumps(plan,indent=2))
    start=time.perf_counter()
    frames,times,indices,fps,crop=module.read_clip(video,*r['interval_s'],r['crop_px'],
                            frame_step=frame_step,storage_path=output/'frames.npy')
    decoded=time.perf_counter()
    try:
        queries=r['provenance']['query_input']
        def progress(done,total):
            p=output/'progress.json';tmp=p.with_suffix('.tmp')
            tmp.write_text(json.dumps({'frames_done':done,'frames_total':total,'wall_seconds':time.perf_counter()-start}));tmp.replace(p)
        tracks,visible,model=module.track_points(frames,queries,checkpoint,threads=r['model']['threads'],progress=progress)
        tracks+=np.asarray(crop[:2])
    finally:
        frames._mmap.close()
    np.savez_compressed(output/'point-tracks.npz',tracks=tracks,visible=visible,times=times,frame_indices=indices)
    lookup={f:i for i,f in enumerate(r['frame_indices'])};original=[lookup[f] for f in indices]
    assert np.allclose(np.asarray(r['times_s'])[original],times,atol=1e-9,rtol=0)
    old=np.asarray(r['tracks_px'])[original];old_visible=np.asarray(r['point_visible'])[original]
    summaries=[]
    for q,name in enumerate(r['point_names']):
        both=visible[:,q]&old_visible[:,q];distance=np.linalg.norm(tracks[:,q]-old[:,q],axis=1)[both]
        summaries.append({'query_index':q,'name':name,'both_visible_samples':int(both.sum()),
                          'visibility_disagreements':int((visible[:,q]!=old_visible[:,q]).sum()),
                          'median_component_disagreement_px':float(np.median(distance)) if len(distance) else None,
                          'max_component_disagreement_px':float(distance.max()) if len(distance) else None})
    result={**tracking_metadata(r),'times_s':times.tolist(),'frame_indices':indices,'tracks_px':tracks.tolist(),
            'point_visible':visible.tolist(),'model':model,'projection':None,
            'sampling_experiment':{**plan,'source_fps':fps,'sample_hz':fps/frame_step,
                                  'decode_seconds':decoded-start,'wall_seconds':time.perf_counter()-start,
                                  'comparison':summaries,'physical_accuracy_verified':False},
            'provenance':{'source_sha256':plan['source_sha256'],'baseline_result':str(baseline.resolve()),
                          'point_tracks_sha256':module.digest(output/'point-tracks.npz')}}
    (output/'result.json').write_text(json.dumps(result,indent=2))
    (output/'frames.npy').unlink()
    return result['sampling_experiment']


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['baseline','video','checkpoint','output','adapter']:p.add_argument('--'+name,required=True)
    p.add_argument('--frame-step',type=int,required=True)
    a=p.parse_args();print(json.dumps(run(a.baseline,a.video,a.checkpoint,a.output,a.frame_step,a.adapter),indent=2))
