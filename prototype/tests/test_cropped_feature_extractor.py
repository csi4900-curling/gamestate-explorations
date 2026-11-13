import cv2
import numpy as np
from prototype.cropped_feature_extractor import CroppedFeatureExtractor


def test_coordinates_return_to_source_space_and_holes_are_preserved():
    mask=np.zeros((40,60),np.uint8);mask[10:30,20:50]=255;mask[15,25]=0
    class Extractor:
        def detectAndCompute(self,image,received):
            assert image.shape==(20,30)
            assert received[5,5]==0
            return [cv2.KeyPoint(3,4,2)],np.array([[1,2]],np.float32)
    points,descriptors=CroppedFeatureExtractor(Extractor()).detectAndCompute(np.zeros_like(mask),mask)
    assert points[0].pt==(23,14)
    assert descriptors.tolist()==[[1,2]]


def test_empty_mask_does_not_invent_region():
    class Forbidden:
        def detectAndCompute(self,*args):raise AssertionError('No region')
    assert CroppedFeatureExtractor(Forbidden()).detectAndCompute(np.zeros((4,4)),np.zeros((4,4),np.uint8))==([],None)
