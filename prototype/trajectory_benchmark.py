"""Score a complete public job against source-bound metric/identity references.

Reference timestamps and visibility define the denominator. Candidate counts,
cross-camera agreement and the run's own calibration are never reference data.
This module changes no predictions. Results include failures and missing tracks.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np
from scipy.optimize import linear_sum_assignment

TARGETS = {'median_position_error_m': .10, 'p95_position_error_m': .25,
           'observable_sample_coverage': 1.0, 'identity_errors': 0,
           'unresolved_identity_samples': 0, 'event_false_positives': 0,
           'event_false_negatives': 0}


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def evaluate(reference, aggregate, *, source_size, source_fps):
    if reference.get('schema_version') != 'metric-trajectory-reference-v1':
        raise ValueError('Unsupported metric trajectory reference')
    if reference['source_sha256'] != aggregate['context']['source_sha256']:
        raise ValueError('Reference belongs to another recording')
    if reference['source_interval_s'] != aggregate['source_interval_s']:
        raise ValueError('Reference must cover the complete requested job interval')
    if reference.get('coordinate_system') != 'delivery_tee_origin_receiving_positive_y_metres':
        raise ValueError('Reference rink coordinate convention must be explicit')
    refs, predictions = reference['events'], aggregate['events']
    if len({r['id'] for r in refs}) != len(refs):
        raise ValueError('Duplicate reference event')
    tolerance=float(reference['event_matching_tolerance_s'])
    if not math.isfinite(tolerance) or tolerance<=0:
        raise ValueError('Reference must declare a positive crossing-time matching tolerance')
    # The dummy alternatives make maximising valid one-to-one event matches
    # precede minimising timing error. An out-of-window pair can never consume
    # the prediction required by a valid pair.
    n,m=len(refs),len(predictions)
    unmatched_cost=max(n,m)+1.
    cost=np.full((n,m+n),unmatched_cost)
    for i,r in enumerate(refs):
        for j,p in enumerate(predictions):
            dt=abs(r['crossing_time_s']-p['event_prediction']['crossing_time_s'])
            cost[i,j]=dt/tolerance if dt<=tolerance else 2*unmatched_cost
    matches={i:j for i,j in zip(*linear_sum_assignment(cost)) if j<m and cost[i,j]<=1.}
    errors=[]; samples=[]; identity_errors=unresolved=missing=ambiguous=switches=expected=0
    event_results=[]
    for i,r in enumerate(refs):
        p=predictions[matches[i]] if i in matches else None
        by_sample={}; histories={}; observed_panels=set()
        if p:
            for segment in p.get('segments',[]):
                panel=segment.get('rink_panel')
                for point in segment.get('geometry_samples',[]):
                    frame=round(point['time_s']*source_fps)
                    by_sample.setdefault((panel,frame),[]).append((segment,point))
        seen=set(); event_rows=[]
        for s in r['samples']:
            key=s['panel'],s['frame_index']
            if key in seen:raise ValueError('Duplicate reference panel/frame')
            seen.add(key)
            if abs(s['time_s']-s['frame_index']/source_fps)>1e-6:
                raise ValueError('Reference frame index and timestamp differ')
            if not s['target_visible']:continue
            expected+=1
            row={'reference_event':r['id'],'panel':s['panel'],'frame_index':s['frame_index'],
                 'time_s':s['time_s'],'status':'missing_prediction','identity':'unresolved'}
            candidates=by_sample.get(key,[])
            event_rows.append(row);samples.append(row)
            if len(candidates)!=1:
                missing+=1;unresolved+=1
                if candidates:ambiguous+=1;row['status']='multiple_predicted_stones'
                continue
            segment,point=candidates[0]
            row['predicted_segment']=segment['segment_id']
            pixel=np.array(point['pixel'],float)*np.array(source_size)/[640.,360.]
            ids=[]
            for stone in s['visible_stones']:
                x0,y0,x1,y1=stone['bbox_source_px_xyxy']
                if x0<=pixel[0]<=x1 and y0<=pixel[1]<=y1:ids.append(stone['stone_id'])
            if len(ids)==1:
                identity=ids[0];row['observed_stone_id']=identity
                row['identity']='correct' if identity==r['stone_id'] else 'wrong_stone'
                if identity!=r['stone_id']:identity_errors+=1
                histories.setdefault(segment['segment_id'],[]).append((s['time_s'],identity))
                observed_panels.add(s['panel'])
            else:
                unresolved+=1
                row['identity']='ambiguous' if ids else 'unresolved'
            xy=point.get('rink_position_m')
            if xy is None:
                missing+=1;row['status']='missing_geometry';continue
            target=np.asarray(s['rink_position_m'],float)
            if target.shape!=(2,) or not np.isfinite(target).all():
                raise ValueError('Visible metric reference must supply finite physical positions')
            error=math.dist(xy,target)
            if not math.isfinite(error):raise ValueError('Nonfinite predicted metric position')
            row.update(status='measured',position_error_m=error)
            errors.append(error)
        for sequence in histories.values():
            sequence=sorted(sequence)
            switches+=sum(a[1]!=b[1] for a,b in zip(sequence,sequence[1:]))
        needs_link={s['panel'] for s in r['samples'] if s['target_visible']}=={'left','right'}
        linked=bool(p and len(p.get('cross_view_links',[]))==1)
        event_results.append({'reference_id':r['id'],'candidate_id':p['candidate_id'] if p else None,
                              'crossing_time_error_s':p['event_prediction']['crossing_time_s']-r['crossing_time_s'] if p else None,
                              'camera_link_present':linked,'camera_link_required':needs_link,
                              'all_reference_identities_correct':bool(event_rows) and all(x['identity']=='correct' for x in event_rows),
                              'coverage':sum(x['status']=='measured' for x in event_rows)/len(event_rows) if event_rows else None})
    provenance=reference['provenance']
    bound=provenance.get('position_error_bound_m')
    bound_valid=(isinstance(bound,(int,float)) and not isinstance(bound,bool)
                 and math.isfinite(bound) and bound>=0)
    independent=(provenance.get('independent') is True and
                 provenance.get('operator_kind') in ('external_human','instrument') and
                 provenance.get('prediction_visible') is False and
                 provenance.get('reference_kind') in ('surveyed_metric_trajectory','independent_metric_reconstruction') and
                 bool(provenance.get('evidence')))
    metrics={'reference_events':n,'event_true_positives':len(matches),'event_false_negatives':n-len(matches),
             'event_false_positives':m-len(matches),'expected_observable_samples':expected,
             'measured_samples':len(errors),'missing_samples':missing,'ambiguous_prediction_samples':ambiguous,
             'observable_sample_coverage':len(errors)/expected if expected else None,
             'median_position_error_m':float(np.median(errors)) if errors else None,
             'p95_position_error_m':float(np.percentile(errors,95)) if errors else None,
             'maximum_position_error_m':max(errors) if errors else None,
             'wrong_stone_samples':identity_errors,'unresolved_identity_samples':unresolved,'identity_switches':switches}
    metrics.update(reference_position_error_bound_m=bound if bound_valid else None,
                   conservative_median_position_error_m=metrics['median_position_error_m']+bound if errors and bound_valid else None,
                   conservative_p95_position_error_m=metrics['p95_position_error_m']+bound if errors and bound_valid else None)
    failures=[]
    if not independent:failures.append('independent_physical_reference_required')
    if not bound_valid:failures.append('reference_position_uncertainty_required')
    if not reference.get('exhaustive_events') or not reference.get('exhaustive_observable_samples'):
        failures.append('exhaustive_reference_coverage_required')
    if not errors:failures.append('no_measured_positions')
    if errors and (metrics['median_position_error_m']>TARGETS['median_position_error_m'] or metrics['p95_position_error_m']>TARGETS['p95_position_error_m']):
        failures.append('position_error_target_failed')
    elif errors and bound_valid and (metrics['conservative_median_position_error_m']>TARGETS['median_position_error_m'] or
                                     metrics['conservative_p95_position_error_m']>TARGETS['p95_position_error_m']):
        failures.append('position_target_not_established_with_reference_uncertainty')
    if not expected or metrics['observable_sample_coverage']!=1.:
        failures.append('observable_trajectory_incomplete')
    if m!=len(matches) or n!=len(matches):failures.append('event_detection_failed')
    if identity_errors or unresolved or switches:failures.append('physical_identity_failed')
    if any(e['camera_link_required'] and not e['camera_link_present'] for e in event_results):
        failures.append('camera_handoff_missing_or_ambiguous')
    return {'schema_version':'trajectory-acceptance-result-v1','accepted':not failures,
            'failure_reasons':failures,'targets':TARGETS,'metrics':metrics,'events':event_results,
            'target_provenance':{'position_error':'User accepted provisional10cm typical/25cm p95; median is the engineering interpretation of typical.',
                                 'other_gates':'Conservative engineering completeness/identity/event checks for this reference interval, not user-approved population error-rate thresholds.'},
            'samples':samples,'reference_provenance':provenance,
            'interpretation':'Position errors use external reference coordinates. Acceptance includes the declared maximum reference position error by the triangle inequality; an unknown reference error cannot certify the targets. Missing tracks and geometry remain in coverage; wrong identities fail even at the correct position. No geometry/trajectory correction is fitted.'}


def run(job, reference_path, output):
    job,reference_path,output=map(Path,(job,reference_path,output))
    if output.exists():raise ValueError('Preserve previous benchmark')
    reference=json.loads(reference_path.read_text())
    path=job/'result/aggregate-rink.json'
    aggregate=json.loads(path.read_text())
    protocol=json.loads((job/'observations/events.json').read_text())
    result=evaluate(reference,aggregate,source_size=protocol['source_size_px'],source_fps=protocol['source_fps'])
    result['inputs_sha256']={'reference':digest(reference_path),'aggregate':digest(path),'public_job_spec':digest(job/'spec.json'),'evaluator':digest(__file__)}
    output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['job','reference','output']:p.add_argument('--'+name,required=True,type=Path)
    a=p.parse_args();result=run(a.job,a.reference,a.output)
    print(json.dumps({k:result[k] for k in ['accepted','failure_reasons','metrics']},indent=2))
    raise SystemExit(0 if result['accepted'] else 1)
