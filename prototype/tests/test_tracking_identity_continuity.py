from prototype.spin.identity import continuity_annotations


def test_one_lost_query_does_not_contaminate_other_identity():
    v=[[True,True],[True,False],[True,True]]
    a=continuity_annotations([1,2,3],v,['delivered','other'])
    assert a['queries'][0]['first_hidden_index'] is None
    assert a['queries'][1]['first_hidden_index']==1
    assert a['queries'][1]['fragments'][-1]['status']=='identity_unverified_after_visibility_loss'
    assert v==[[True,True],[True,False],[True,True]] and not a['predictions_modified']


def test_every_reappearance_after_loss_remains_unverified():
    a=continuity_annotations([1,2,3,4,5],[[True],[False],[True],[False],[True]],['cap'])
    assert len(a['queries'][0]['fragments'])==3
    assert all(f['status']=='identity_unverified_after_visibility_loss' for f in a['queries'][0]['fragments'][1:])


def test_hidden_seed_does_not_certify_later_identity():
    a=continuity_annotations([1,2],[[False],[True]],['cap'])
    assert a['queries'][0]['fragments'][0]['status']=='identity_unverified_after_visibility_loss'
    assert not a['queries'][0]['physical_identity_verified']
