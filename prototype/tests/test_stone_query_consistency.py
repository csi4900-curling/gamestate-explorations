from prototype.stone_query_consistency import frame_conflicts


def test_shared_stone_box_preserves_both_query_ids_as_conflict():
    r=frame_conflicts([[2,2],[3,3],[20,20]],[True,True,False],[{'bbox_xyxy':[0,0,10,10]}])
    assert r['shared_box_conflicts']==[{'detection_index':0,'query_indices':[0,1]}]
    assert r['query_box_membership'][2]==[]


def test_overlapping_boxes_are_ambiguous_not_forced_assignments():
    r=frame_conflicts([[2,2],[3,3]],[True,True],[{'bbox_xyxy':[0,0,10,10]},{'bbox_xyxy':[1,1,11,11]}])
    assert r['ambiguous_box_query_indices']==[0,1]
    assert r['shared_box_conflicts']==[]
