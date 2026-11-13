import numpy as np
from prototype.match_observation import project_body


def test_projection_at_infinity_retains_explicit_failure():
    H=np.array([[1.,0,0],[0,1,0],[0,1,-10]])
    raw,adjusted,diag=project_body(H,[5,10],(0,0,320,360),None,None)
    assert raw is None and adjusted is None
    assert diag['status']=='undefined_projection'


def test_missing_height_model_does_not_discard_available_raw_projection():
    raw,adjusted,diag=project_body(np.eye(3),[5,10],(0,0,320,360),None,None)
    assert raw==[5,10] and adjusted is None
    assert diag['status']=='unavailable'
