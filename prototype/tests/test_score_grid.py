from prototype.score_grid import parse_end_cells


def token(text,box):
    return {'text':text,'normalized':text.replace(' ',''),'bounds':box,'confidence':.9}


def test_observed_grid_has_no_fixed_end_count_or_pixel_origin():
    tokens=[token('END',[10,10,30,20]),token('9',[90,10,100,20]),token('10',[110,10,120,20]),token('CAN',[10,30,30,40]),token('SWE',[10,50,30,60]),token('3',[90,30,100,40]),token('0',[90,50,100,60])]
    r=parse_end_cells(tokens,['CAN','SWE'])
    assert r['end_score_cells']['9']['CAN']['value']==3
    assert r['end_score_cells']['9']['SWE']['value']==0
    assert r['current_end'] is None


def test_merged_and_duplicate_digits_are_not_guessed():
    tokens=[token('END',[10,10,30,20]),token('1',[40,10,50,20]),token('2',[60,10,70,20]),token('CAN',[10,30,30,40]),token('012',[35,30,65,40])]
    assert parse_end_cells(tokens,['CAN','SWE'])['end_score_cells']['1']['CAN']['value'] is None
    tokens.extend([token('0',[40,30,50,40]),token('1',[40,30,50,40])])
    assert parse_end_cells(tokens,['CAN','SWE'])['end_score_cells']['1']['CAN']['value'] is None


def test_merged_header_is_not_a_fictitious_end_number():
    tokens=[token('END',[0,0,10,10]),token('1',[20,0,30,10]),token('2',[40,0,50,10]),token('3456',[60,0,140,10]),token('7',[150,0,160,10]),token('8',[170,0,180,10])]
    assert set(parse_end_cells(tokens,['CAN','SWE'])['end_score_cells'])=={'1','2','7','8'}


def test_active_end_is_read_only_from_explicit_marker_not_completed_cells():
    tokens=[token('END',[0,0,10,10]),token('1',[20,0,30,10]),token('2',[40,0,50,10]),token('CAN',[0,20,10,30]),token('0>',[15,20,55,30])]
    r=parse_end_cells(tokens,['CAN','SWE'])
    assert r['current_end']==2
    assert r['current_end_evidence']['team_row']=='CAN'
    tokens[-1]=token('01',[15,20,55,30])
    assert parse_end_cells(tokens,['CAN','SWE'])['current_end'] is None
