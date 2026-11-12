import json

from prototype.score_tracking import build


def test_unknowns_staleness_and_score_changes_never_backdate_values(tmp_path):
    path = tmp_path/'scores.jsonl'
    values = [(None,None),(0,0),(None,None),(1,0),(1,0),(0,0),(1,0)]
    rows = [{'time_s':float(i), 'totals':{t:{'value':v} for t,v in zip(('A','B'),pair)}}
            for i,pair in enumerate(values)]
    path.write_text(''.join(json.dumps(r)+'\n' for r in rows))
    result = build(path)
    timeline = result['timeline']
    assert timeline[0]['totals']['A']['value'] is None
    assert timeline[2]['totals']['A']['value'] == 0
    assert timeline[2]['totals']['A']['observed_at_s'] == 1
    assert timeline[3]['totals']['A']['value'] == 1
    assert timeline[5]['totals']['A']['value'] == 1
    assert timeline[5]['raw_totals']['A'] == 0
    assert result['conflicts']['A'][0]['time_s'] == 5
    assert not result['independent_score_accuracy_measured']
    assert result['future_observations_used_for_sequence_selection']


def test_equal_support_conflict_does_not_choose_arbitrarily(tmp_path):
    path = tmp_path/'scores.jsonl'
    path.write_text(''.join(json.dumps({'time_s':i,'totals':{'A':{'value':v}}})+'\n'
                            for i,v in enumerate([1,0])))
    result = build(path)
    assert all(r['totals']['A']['value'] is None for r in result['timeline'])
    assert len(result['conflicts']['A']) == 2
