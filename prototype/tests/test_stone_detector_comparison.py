from prototype.scripts.compare_stone_detectors import score


def test_duplicate_object_is_false_positive_and_ignore_does_not_hide_true_match():
    annotation={'boxes_xyxy':[[0,0,10,10]],'ignore_regions_xyxy':[[0,0,20,20]]}
    result=score([{'pixel':[5,5]},{'pixel':[15,15]},{'pixel':[30,30]}],annotation,[0,0,40,40])
    assert (result['tp'],result['fp'],result['fn'],result['ignored'])==(1,1,0,1)
    annotation['ignore_regions_xyxy']=[]
    result=score([{'pixel':[5,5]},{'pixel':[6,6]}],annotation,[0,0,40,40])
    assert (result['tp'],result['fp'],result['fn'])==(1,1,0)


def test_missing_objects_and_other_panel_are_explicit():
    result=score([{'pixel':[5,5]}],{'boxes_xyxy':[[325,0,335,10]],'ignore_regions_xyxy':[]},[320,0,640,360])
    assert result['tp']==0 and result['fp']==0 and result['fn']==1
