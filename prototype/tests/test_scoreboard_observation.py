from prototype.scoreboard_observation import parse_totals


def box(x,y,w=20,h=20):return [[x,y],[x+w,y],[x+w,y+h],[x,y+h]]

def read(texts,boxes):return parse_totals(texts,[.99]*len(texts),boxes,['CAN','SWE'])

def test_observed_zero_is_distinct_from_unknown():
    r=read(['TOTAL','CAN','SWE','0'],[box(100,0),box(0,30),box(0,60),box(100,30)])
    assert r['totals']['CAN']['value']==0
    assert r['totals']['SWE']['value'] is None
    assert r['current_end'] is None

def test_occluded_header_does_not_guess_column():
    r=read(['CAN','SWE','6','6'],[box(0,30),box(0,60),box(100,30),box(100,60)])
    assert all(t['value'] is None for t in r['totals'].values())

def test_duplicate_score_observation_is_ambiguous():
    r=read(['TOTAL','CAN','0','1'],[box(100,0),box(0,30),box(100,30),box(100,30)])
    assert r['totals']['CAN']['value'] is None

def test_other_end_column_does_not_become_total():
    r=read(['TOTAL','CAN','5','3'],[box(100,0),box(0,30),box(60,30),box(100,30)])
    assert r['totals']['CAN']['value']==3

def test_missing_team_label_does_not_guess_identity():
    r=read(['TOTAL','6'],[box(100,0),box(100,30)])
    assert r['totals']['CAN']['value'] is None


def test_displayed_marker_does_not_claim_current_physical_end():
    r=read(['END','1','2','CAN','0>'],
           [box(0,0,10,10),box(20,0,10,10),box(40,0,10,10),
            box(0,20,10,10),box(15,20,40,10)])
    assert r['displayed_end']==2
    assert r['current_end'] is None
    assert r['displayed_end_evidence']['team_row']=='CAN'
