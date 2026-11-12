from prototype.score_sequence import infer


def rows(values):return [{'time_s':i,'totals':{'A':{'value':v}}} for i,v in enumerate(values)]


def test_isolated_wrong_increase_remains_visible_as_conflicting_evidence():
    data=rows([0,1,4,1,1,3]);r=infer(data)
    assert r['analyses']['A']['observations'][2]['status']=='conflicts_with_maximum_support_chronology'
    assert [x['totals']['A']['value'] for x in r['timeline']]==[0,1,1,1,1,3]
    assert data[2]['totals']['A']['value']==4
    assert r['timeline'][2]['totals']['A']['age_s']==1


def test_ties_are_not_silently_resolved():
    r=infer(rows([1,2,1]))
    assert r['analyses']['A']['optimal_sequence_count']==2
    assert r['analyses']['A']['observations'][1]['status']=='ambiguous_maximum_support_sequence'
    assert r['timeline'][-1]['totals']['A']['value']==1
    assert r['timeline'][-1]['totals']['A']['age_s']==2


def test_unknown_is_not_zero_and_real_zero_is_preserved():
    r=infer(rows([None,0,None]))
    assert r['timeline'][0]['totals']['A']['value'] is None
    assert r['timeline'][1]['totals']['A']['value']==0
    assert r['timeline'][2]['totals']['A']['age_s']==1
