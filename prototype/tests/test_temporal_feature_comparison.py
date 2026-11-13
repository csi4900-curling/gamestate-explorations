import cv2
import numpy as np
from prototype.temporal_feature_comparison import PropagatedFeatures


def test_propagates_only_supported_points_and_preserves_descriptor_identity(monkeypatch):
    class Extractor:
        def detectAndCompute(self, gray, mask):
            return [cv2.KeyPoint(float(x), 2., 1.) for x in [2, 3, 4, 5]], np.arange(8).reshape(4, 2)
    tracker = PropagatedFeatures(Extractor())
    gray = np.zeros((10, 10), np.uint8)
    mask = np.ones_like(gray)
    tracker.detectAndCompute(gray, mask)
    def flow(*args):
        return np.array([[[3, 2]], [[4, 2]], [[11, 2]], [[6, 2]]], np.float32), np.array([[1], [0], [1], [1]]), None
    monkeypatch.setattr(cv2, 'calcOpticalFlowPyrLK', flow)
    mask[2, 6] = 0
    points, descriptors = tracker.detectAndCompute(gray, mask)
    assert [p.pt for p in points] == [(3., 2.)]
    np.testing.assert_array_equal(descriptors, [[0, 1]])
    assert tracker.initializations == 1 and tracker.flow_calls == 1


def test_empty_features_are_not_silently_reinitialized():
    class Extractor:
        def detectAndCompute(self, gray, mask): return [], None
    tracker = PropagatedFeatures(Extractor())
    for _ in range(3):
        keypoints, descriptors = tracker.detectAndCompute(np.zeros((10, 10), np.uint8), None)
        assert keypoints == [] and descriptors is None
    assert tracker.initializations == 1 and tracker.flow_calls == 0
