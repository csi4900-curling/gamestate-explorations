import cv2
import numpy as np
import pytest
from prototype.calibrated_camera_geometry import panel_features,CalibratedCameraGeometry
from prototype.tests.test_rink_calibration import bundle


def test_foreground_mask_excludes_descriptor_centres_without_replacing_source_pixels():
    rng=np.random.default_rng(23)
    image=rng.integers(120,255,(1080,1920,3),np.uint8);original=image.copy()
    mask=np.zeros((1080,1920),np.uint8);mask[:,100:800]=255
    points,descriptors=panel_features(image,'left',mask)
    assert len(points)>0
    # OpenCV tests its integer mask at the rounded keypoint location; SIFT
    # retains the subpixel location (which can lie <0.5 px across an edge).
    assert all(mask[round(float(y)),round(float(x))]==0 for x,y in points)
    assert np.array_equal(image,original)
    with pytest.raises(ValueError,match='canonical source pixels'):
        panel_features(image,'left',np.zeros((10,10),np.uint8))


def test_one_current_foreground_prediction_is_shared_by_both_cameras(tmp_path,monkeypatch):
    from prototype import camera_foreground
    class FakeForeground:
        def __init__(self,*args,**kwargs):
            self.frames=0;self.seconds=0.;self.provenance={'backend':'synthetic test stub'}
        def mask(self,image):
            self.frames+=1
            return np.zeros(image.shape[:2],np.uint8)
    monkeypatch.setattr(camera_foreground,'CameraForeground',FakeForeground)
    path,_,image=bundle(tmp_path)
    g=CalibratedCameraGeometry(path,alignment='static_feature_similarity',
                               foreground_checkpoint='test-stub',foreground_sha256='stub')
    assert g.foreground.frames==1  # Both source panels use the same source PNG.
    result=g.observe(image,1.)
    assert all(v[0] is not None for v in result.values())
    assert g.foreground.frames==2  # One full-frame mask, not one per panel.
    assert g.provenance()['foreground_mask_frames']==2
