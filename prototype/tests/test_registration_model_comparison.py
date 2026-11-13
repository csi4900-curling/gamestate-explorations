import json
import cv2
import numpy as np
import pytest
from prototype.registration_model_comparison import compare


@pytest.mark.parametrize('perspective', [False, True])
def test_shared_correspondences_expose_similarity_model_limit(tmp_path,monkeypatch,perspective):
    import prototype.registration_model_comparison as module
    a=np.array([(x,y) for x in [40,150,300,450,590] for y in [30,100,180,260,330]],np.float32)
    transform=np.array([[1.,0.,4.],[0.,1.,3.],[.001 if perspective else 0.,0.,1.]])
    b=cv2.perspectiveTransform(a.reshape(-1,1,2),transform).reshape(-1,2)
    def features(image,region):
        xy=b if image[0,0,0] else a
        return [cv2.KeyPoint(float(x),float(y),1) for x,y in xy],np.eye(len(a),dtype=np.float32)
    monkeypatch.setattr(module,'features',features)
    paths=[]
    for i in [0,1]:
        path=tmp_path/f'{i}.png';cv2.imwrite(str(path),np.full((360,640,3),i,np.uint8));paths.append(path)
    ref=tmp_path/'reference.json'
    ref.write_text(json.dumps({'reference_image':str(paths[0]),'normalization_size':[640,360],
        'region':[0,0,640,360],'landmarks':{str(i):p.tolist() for i,p in enumerate(a)},
        'targets':[{'image':str(paths[1]),'source_frame':1,'landmarks':{str(i):p.tolist() for i,p in enumerate(b)}}]}))
    result=compare(ref,tmp_path/'output.json')['frames'][0]['models']
    assert result['projective']['max_landmark_error_px']<.001
    if perspective:
        assert result['similarity']['max_landmark_error_px']>5
    else:
        assert result['similarity']['max_landmark_error_px']<.001
    with pytest.raises(ValueError,match='Preserve existing'):
        compare(ref,tmp_path/'output.json')
