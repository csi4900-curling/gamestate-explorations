from prototype.camera_motion_role import recover_missing_role

EVENT = dict(observed_bracket_s=[1.0,1.1],track_id=7,crossing_point_normalized=[.2,.3])
MISSING = dict(role='unassigned',reason='missing_or_undefined_geometry')
SAMPLES = [(.8,[0,3]),(.9,[0,2.8]),(1.,None),(1.1,None),(1.2,[0,2.2]),(1.3,[0,2])]


def test_missing_bracket_can_recover_direction_without_filling_it():
    result=recover_missing_role(EVENT,SAMPLES,.1,MISSING)
    assert result['role']=='receiving' and result['panel']=='left'
    assert result['original_role_evidence'] is MISSING
    assert result['mapped_sample_counts']==[2,2] and not result['physical_identity_verified']


def test_missing_track_reversal_and_existing_direction():
    assert recover_missing_role(EVENT,SAMPLES[:2]+SAMPLES[3:],.1,MISSING) is MISSING
    assert recover_missing_role(EVENT,SAMPLES[:-1]+[(1.3,[0,3.2])],.1,MISSING) is MISSING
    known=dict(role='departure')
    assert recover_missing_role(EVENT,SAMPLES,.1,known) is known
