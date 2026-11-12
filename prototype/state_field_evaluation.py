"""Exact field agreement with explicit readable/unknown reference boundaries."""


def evaluate_fields(predictions, references, fields):
    by_time={r['time_s']:r for r in predictions}
    if len(by_time)!=len(predictions):raise ValueError('Duplicate prediction timestamps')
    if len({r['time_s'] for r in references})!=len(references):raise ValueError('Duplicate reference timestamps')
    scores={field:{'readable_reference':0,'correct':0,'incorrect':0,'abstained_on_readable':0,
                   'unreadable_reference':0,'prediction_on_unreadable':0} for field in fields}
    comparisons=[]
    for ref in references:
        pred=by_time.get(ref['time_s'],{})
        for field in fields:
            actual=ref.get(field);value=pred.get(field);s=scores[field]
            if actual is None:
                s['unreadable_reference']+=1;s['prediction_on_unreadable']+=value is not None
                status='unverifiable_prediction' if value is not None else 'both_unknown'
            else:
                s['readable_reference']+=1
                if value is None:s['abstained_on_readable']+=1;status='abstained'
                elif value==actual:s['correct']+=1;status='correct'
                else:s['incorrect']+=1;status='incorrect'
            comparisons.append({'time_s':ref['time_s'],'field':field,'reference':actual,'prediction':value,'status':status})
    for s in scores.values():
        readable=s['readable_reference'];answered=s['correct']+s['incorrect']
        s['correct_fraction_of_readable']=s['correct']/readable if readable else None
        s['accuracy_among_verifiable_answers']=s['correct']/answered if answered else None
        s['answer_coverage_of_readable']=answered/readable if readable else None
    return {'fields':scores,'comparisons':comparisons,'unknown_reference_policy':'Predictions on unreadable reference fields are unverifiable, not automatically correct or incorrect.'}
