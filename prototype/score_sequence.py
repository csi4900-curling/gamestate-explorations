"""Chronological score inference with raw OCR evidence retained.

Find maximum-cardinality nondecreasing subsequences of observed totals. No score
labels or confidence cutoff are used. This assumes a single live match with
nondecreasing true totals; replays, scoreboard corrections and OCR errors can
violate the observation order. Output is explicitly inferred, never relabelled
as direct observation or calibrated confidence. Ties remain ambiguous.
"""
import json
from pathlib import Path


def classify_observations(rows,team):
    observed=[(i,r['totals'][team]['value']) for i,r in enumerate(rows) if r['totals'][team]['value'] is not None]
    n=len(observed)
    if not n:return {'maximum_support':0,'optimal_sequence_count':0,'observations':[]}
    forward=[1]*n;backward=[1]*n;prefix_count=[1]*n;suffix_count=[1]*n
    for i,(_,value) in enumerate(observed):
        previous=[j for j in range(i) if observed[j][1]<=value]
        if previous:
            best=max(forward[j] for j in previous);forward[i]=best+1
            prefix_count[i]=sum(prefix_count[j] for j in previous if forward[j]==best)
    for i in range(n-1,-1,-1):
        following=[j for j in range(i+1,n) if observed[j][1]>=observed[i][1]]
        if following:
            best=max(backward[j] for j in following);backward[i]=best+1
            suffix_count[i]=sum(suffix_count[j] for j in following if backward[j]==best)
    optimum=max(forward);ways=sum(prefix_count[i] for i in range(n) if forward[i]==optimum)
    classified=[]
    for i,(source_index,value) in enumerate(observed):
        supported=forward[i]+backward[i]-1==optimum
        paths=prefix_count[i]*suffix_count[i] if supported else 0
        status='required_by_all_maximum_support_sequences' if paths==ways else 'ambiguous_maximum_support_sequence' if paths else 'conflicts_with_maximum_support_chronology'
        classified.append({'source_observation_index':source_index,'time_s':rows[source_index]['time_s'],'value':value,
                           'status':status,'optimal_sequences_including_observation':paths,
                           'raw_observation_unchanged':True})
    return {'maximum_support':optimum,'optimal_sequence_count':ways,'observations':classified}


def infer(rows):
    if any(a['time_s']>=b['time_s'] for a,b in zip(rows,rows[1:])):raise ValueError('Score observations must be chronological')
    teams=sorted({team for row in rows for team in row['totals']})
    analyses={team:classify_observations(rows,team) for team in teams}
    timeline=[];last={};by_index={team:{x['source_observation_index']:x for x in analysis['observations']} for team,analysis in analyses.items()}
    for i,row in enumerate(rows):
        for team in teams:
            candidate=by_index[team].get(i)
            if candidate and candidate['status']=='required_by_all_maximum_support_sequences':
                last[team]={'value':candidate['value'],'observed_at_s':row['time_s'],'source_observation_index':i}
        timeline.append({'time_s':row['time_s'],'totals':{team:{**last[team],'age_s':row['time_s']-last[team]['observed_at_s'],'provenance':'inferred_chronological_score_from_OCR'} if team in last else {'value':None,'provenance':'unknown'} for team in teams},
                         'current_end':None,'future_observations_used_for_sequence_selection':True})
    return {'method':'Maximum-cardinality nondecreasing OCR subsequences, retaining all ties',
            'assumption':'One live chronological match; true cumulative team scores do not decrease. Replays and scoreboard corrections are not classified by this method.',
            'limitations':['Consistency is not score accuracy; repeated OCR errors can dominate.','Inference uses the whole sequence; not an online score reader.','Current end and points currently lying are not inferred from totals.'],
            'analyses':analyses,'timeline':timeline,'independent_score_accuracy_measured':False}


def run(input_path,output):
    from prototype.match_observation import sha
    input_path=Path(input_path);output=Path(output)
    if output.exists():raise ValueError('Preserve previous score inference')
    rows=[json.loads(line) for line in input_path.read_text().splitlines()]
    result=infer(rows);result['source_observations_sha256']=sha(input_path);result['code_sha256']=sha(__file__)
    output.write_text(json.dumps(result,indent=2));return result


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--observations',required=True);parser.add_argument('--output',required=True)
    a=parser.parse_args();run(a.observations,a.output)
