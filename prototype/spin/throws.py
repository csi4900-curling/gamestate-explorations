"""Dense two-view throw review using upstream tracking and preserved associations.

Does not introduce new association thresholds or turn local point IDs into
verified stone identities. Unknown handoffs and missing samples remain explicit.
"""
import argparse
import json
from pathlib import Path
import time

from .pipeline import candidate_config, run
from .point_tracking import digest, decoder_identity
from .throw_report import write_report
from .identity import continuity_annotations


def event_source_time(event):
    """Keep the candidate seekable even when all dense tracks fail."""
    value=event.get('event_prediction',{}).get('crossing_time_s')
    if value is not None:
        return float(value)
    times=[p['time_s'] for s in event.get('segments',[]) for p in s.get('pixel_points',[])]
    return min(times) if times else None


def association(event):
    segments = {s['segment_id']: s for s in event['segments']}
    links = event.get('cross_view_links', [])
    referenced = []
    issues = list(event.get('association_issues',[]))
    for link in links:
        a, b = link['departure_segment'], link['receiving_segment']
        if a not in segments or b not in segments:
            issues.append('link_references_missing_segment')
            continue
        if segments[a].get('role') != 'departure' or segments[b].get('role') != 'receiving':
            issues.append('link_roles_inconsistent')
            continue
        referenced.extend([a, b])
    if len(referenced) != len(set(referenced)):
        issues.append('multiple_links_claim_same_segment')
    return {
        'status': 'ambiguous' if issues or len(links) > 1 else 'provisional' if links else 'unresolved',
        'links': links, 'issues': issues,
        'basis': event.get('association_method','Existing aggregate colour/time/geometry rules, unchanged. CoTracker does not predict this handoff.'),
        'physical_identity_verified': False,
    }


def visibility_intervals(result):
    """Retain model-hidden runs; interval coverage is not identity accuracy."""
    times = result['times_s']
    runs = []
    for i, t in enumerate(times):
        visible = bool(result['point_visible'][i][0])
        if not runs or runs[-1]['model_visible'] != visible:
            runs.append({'start_s': t, 'end_s': t, 'model_visible': visible, 'samples': 0})
        runs[-1]['end_s'] = t
        runs[-1]['samples'] += 1
    return runs


def handoff_observations(assoc, results):
    rows = []
    for link in assoc['links']:
        a, b = (results.get(link[k]) for k in ('departure_segment', 'receiving_segment'))
        aa = [t for t,v in zip(a['times_s'],a['point_visible']) if v[0]] if a else []
        bb = [t for t,v in zip(b['times_s'],b['point_visible']) if v[0]] if b else []
        row = {'departure_segment': link['departure_segment'], 'receiving_segment': link['receiving_segment'],
               'status': 'model_visible_endpoints' if aa and bb else 'missing_dense_endpoint',
               'physical_identity_verified': False, 'interpolated': False}
        if aa and bb:
            row.update(departure_last_visible_s=aa[-1], receiving_first_visible_s=bb[0],
                       interval_s=[aa[-1],bb[0]], gap_s=max(0,bb[0]-aa[-1]),
                       overlap_s=max(0,aa[-1]-bb[0]))
        rows.append(row)
    return rows


def run_throws(video, aggregate_path, output, checkpoint, *, candidate_ids=None, mode='online',
               device='cpu', threads=4, cache_manifest=None, expected_decoder_sha=None, stone_detector_checkpoint=None, projection_config=None, stone_colour_config=None, stone_detector_head='checkpoint', stone_detector_threads=None, tracking_progress_dir=None):
    started=time.perf_counter()
    if stone_colour_config is not None and stone_detector_checkpoint is None:
        raise ValueError('Learned colour requires learned stone source crops')
    from .projection import feature_heights
    heights = feature_heights(json.loads(Path(projection_config).read_text())) if projection_config is not None else None
    if expected_decoder_sha is not None and decoder_identity()['build_sha256']!=expected_decoder_sha:
        raise ValueError('Tracking OpenCV build differs from main pipeline; align environments')
    video, aggregate_path, output = Path(video),Path(aggregate_path),Path(output)
    aggregate=json.loads(aggregate_path.read_text())
    if aggregate['context']['source_sha256'] != digest(video):
        raise ValueError('Aggregate and video differ')
    wanted=set(candidate_ids or [])
    events=[e for e in aggregate['events'] if not wanted or e['candidate_id'] in wanted]
    if wanted - {e['candidate_id'] for e in events}:
        raise ValueError('Unknown requested candidate')
    if output.exists():
        raise ValueError('Output exists; preserve previous runs')
    output.mkdir(parents=True)
    (output/'code-snapshot').mkdir()
    for p in Path(__file__).parent.glob('*.py'):
        (output/'code-snapshot'/p.name).write_bytes(p.read_bytes())
    diagnostic_source=Path(__file__).parents[1]/'stone_query_consistency.py'
    (output/'code-snapshot'/diagnostic_source.name).write_bytes(diagnostic_source.read_bytes())
    stone_detector=None
    if stone_detector_checkpoint is not None:
        from prototype.stone_detector import StoneDetector
        stone_detector=StoneDetector(stone_detector_checkpoint,device=device,threads=threads if stone_detector_threads is None else stone_detector_threads,head=stone_detector_head)
    stone_colour_model=None
    if stone_colour_config is not None:
        from prototype.stone_colour_model import StoneColourModel
        stone_colour_model=StoneColourModel(stone_colour_config)
        (output/'colour-config.json').write_bytes(Path(stone_colour_config).read_bytes())
        source=Path(__file__).parents[1]/'stone_colour_model.py'
        (output/'code-snapshot'/source.name).write_bytes(source.read_bytes())
    caches=json.loads(Path(cache_manifest).read_text()) if cache_manifest else {}
    report={'schema_version':'two-view-dense-development-v1','events':[],
            'scope':'Existing provisional handoffs with dense per-camera point tracking; physical identity and geometry unvalidated.',
            'source_sha256':digest(video),'aggregate_sha256':digest(aggregate_path),
            'source_interval_s':aggregate.get('source_interval_s'),
            'checkpoint_sha256':digest(checkpoint), 'physical_identity_verified':False,
            'selection':sorted(wanted) if wanted else 'all aggregate events',
            'code_sha256':{p.name:digest(p) for p in (output/'code-snapshot').glob('*.py')}}
    if heights is not None:
        report['projection_config']={'feature_heights_m':heights,'file_sha256':digest(projection_config)}
    if stone_detector is not None:
        report['stone_detector']=stone_detector.provenance
        report['scope'] += ' Learned scene initialization; event and handoff methods are recorded in the supplied aggregate.'
    observed_run=aggregate.get('provenance',{}).get('match_observation_run')
    if observed_run:
        observed_run=Path(observed_run)
        if digest(observed_run/'match-observations.jsonl')!=aggregate['provenance']['board_observations_sha256']:
            raise ValueError('Match observation source changed after aggregate construction')
        report['match_observation_run']=str(observed_run.resolve())
    for ei,event in enumerate(events):
        row={'candidate_id':event['candidate_id'],'association':association(event),
             'event_time_s':event_source_time(event),
             'baseline_failure_reasons':event.get('failure_reasons',[]),'segments':[]}
        results={}
        # Keep all segments, including ones not linked to the other camera.
        for si,segment in enumerate(event['segments']):
            sid=segment['segment_id'];folder=f'event-{ei:04d}/segment-{si:02d}'
            entry={'segment_id':sid,'camera':segment['camera'],'role':segment.get('role'),
                   'status':'pending','report':None}
            row['segments'].append(entry)
            if segment['camera'] not in ('left_split','right_split') or not segment.get('pixel_points'):
                entry.update(status='unavailable',reason='No nonempty split-camera observations')
                continue
            config_path=output/f'config-{ei:04d}-{si:02d}.json'
            try:
                config=candidate_config(video,aggregate_path,sid,receiving_scene=True)
                if tracking_progress_dir is not None:
                    config['tracking_progress_directory']=str(Path(tracking_progress_dir).resolve())
                if heights is not None:
                    config['feature_heights_m']=heights
                if stone_detector is not None:
                    config['stone_detector']=stone_detector.provenance
                config_path.write_text(json.dumps(config,indent=2)+'\n')
                result=run(video,config_path,output/folder,checkpoint=checkpoint,device=device,mode=mode,
                           threads=threads,aggregate_path=aggregate_path,reuse_result=caches.get(sid),stone_detector=stone_detector)
                results[sid]=result
                entry.update(status='tracked',report=f'{folder}/index.html',result=f'{folder}/result.json',
                             result_sha256=digest(output/folder/'result.json'),
                             visibility_intervals=visibility_intervals(result),
                             times_s=result['times_s'],tracks_px=result['tracks_px'],point_visible=result['point_visible'],
                             fps=result['fps'],point_names=result['point_names'],point_kinds=result.get('point_kinds'),
                             identity_continuity=continuity_annotations(result['times_s'],result['point_visible'],result['point_names']),
                             episode_policy=result['config'].get('episode_policy'),
                             scene_initialization=result['config'].get('scene_initialization'),
                             projection=result.get('projection'),model=result['model'])
                if observed_run is not None:
                    from prototype.stone_query_consistency import audit
                    try:
                        entry['detector_consistency'] = audit(
                            output/folder/'result.json', observed_run,
                            output/folder/'detector-consistency.json')
                    except (ValueError, OSError, KeyError) as exc:
                        entry['detector_consistency_error'] = f'{type(exc).__name__}: {exc}'
            except (ValueError, RuntimeError, OSError) as exc:
                entry.update(status='failed',reason=f'{type(exc).__name__}: {exc}')
            (output/'progress.json').write_text(json.dumps({'event':row},indent=2)+'\n')
        row['handoffs']=handoff_observations(row['association'],results)
        row['missing_roles']=[role for role in ('departure','receiving')
                              if not any(s['role']==role and s['status']=='tracked' for s in row['segments'])]
        report['events'].append(row)
    report['wall_seconds']=time.perf_counter()-started
    report['summary']={'events':len(events),
                       'segments_tracked':sum(s['status']=='tracked' for e in report['events'] for s in e['segments']),
                       'segments_failed':sum(s['status']=='failed' for e in report['events'] for s in e['segments']),
                       'provisional_handoffs':sum(e['association']['status']=='provisional' for e in report['events']),
                       'verified_physical_handoffs':0}
    (output/'result.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    if stone_colour_model is not None:
        report['stone_colour_model']=stone_colour_model.provenance
        (output/'result.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
        write_report(report,output,video,stone_detector=stone_detector,stone_colour_model=stone_colour_model)
    elif stone_detector is None:
        write_report(report,output,video)
    else:
        write_report(report,output,video,stone_detector=stone_detector)
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('video','aggregate','output','checkpoint'):p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--stone-detector-checkpoint',type=Path);p.add_argument('--expected-decoder-sha');p.add_argument('--candidate',action='append');p.add_argument('--cache-manifest',type=Path)
    p.add_argument('--stone-detector-head',choices=['checkpoint','end2end','conventional'],default='checkpoint')
    p.add_argument('--stone-detector-threads',type=int)
    p.add_argument('--tracking-progress-dir',type=Path,help='Exact-contract online CPU CoTracker progress checkpoints')
    p.add_argument('--stone-colour-config',type=Path,help='Optional learned snapshot colour ranking configuration; not verified team assignment')
    p.add_argument('--projection-config',type=Path,help='JSON feature heights in metres; recorded in segment configs and end-state projections')
    p.add_argument('--mode',choices=['online','offline'],default='online')
    p.add_argument('--device',default='cpu');p.add_argument('--threads',type=int,default=4)
    a=p.parse_args();r=run_throws(a.video,a.aggregate,a.output,a.checkpoint,candidate_ids=a.candidate,
                                 mode=a.mode,device=a.device,threads=a.threads,cache_manifest=a.cache_manifest,expected_decoder_sha=a.expected_decoder_sha,stone_detector_checkpoint=a.stone_detector_checkpoint,projection_config=a.projection_config,stone_colour_config=a.stone_colour_config,stone_detector_head=a.stone_detector_head,stone_detector_threads=a.stone_detector_threads,tracking_progress_dir=a.tracking_progress_dir)
    print(json.dumps(r['summary']))

if __name__=='__main__':main()
