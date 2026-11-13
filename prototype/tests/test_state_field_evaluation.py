from prototype.state_field_evaluation import evaluate_fields


def test_zero_unknown_abstention_and_unsupported_answer_remain_distinct():
    ref=[{'time_s':0,'score':0},{'time_s':1,'score':2},{'time_s':2,'score':None}]
    pred=[{'time_s':0,'score':0},{'time_s':1,'score':None},{'time_s':2,'score':5}]
    r=evaluate_fields(pred,ref,['score']);s=r['fields']['score']
    assert s['correct']==1 and s['abstained_on_readable']==1
    assert s['incorrect']==0 and s['prediction_on_unreadable']==1
    assert s['correct_fraction_of_readable']==.5
    assert s['accuracy_among_verifiable_answers']==1
