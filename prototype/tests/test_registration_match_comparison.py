import cv2
import numpy as np

from prototype.registration_match_comparison import reciprocal_pairs


def test_reciprocal_filter_removes_many_to_one_descriptor_matches():
    source = np.array([[0., 0.], [.1, 0.], [10., 0.]], np.float32)
    target = np.array([[0., 0.], [9., 0.], [20., 0.]], np.float32)
    baseline = cv2.BFMatcher().knnMatch(source, target, k=2)
    assert baseline[0][0].trainIdx == baseline[1][0].trainIdx
    pairs = reciprocal_pairs(source, target, cv2.BFMatcher)
    assert [(p[0].queryIdx, p[0].trainIdx) for p in pairs] == [(0, 0), (2, 1)]
    # Keep the second neighbour for the unchanged caller's original ratio test.
    assert all(len(pair) == 2 for pair in pairs)
