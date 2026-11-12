import math
import cv2
import numpy as np
import pytest
from prototype.spin.frame_handle_probe import mask_axis, obb_axis
from prototype.spin.signed_rotation import summarize


def test_empty_mask_abstains():
    assert mask_axis(np.zeros((32,32),np.uint8)) is None


def test_obb_major_axis_does_not_depend_on_corner_start():
    corners = np.array([[2,3],[12,3],[12,6],[2,6]])
    for i in range(4):
        selected = obb_axis(np.roll(corners,i,axis=0))
        assert sorted(selected.tolist()) == [[2,6],[12,6]]


def test_independent_frame_axes_can_follow_a_synthetic_reversal():
    times = np.arange(121)/30
    phase = np.where(times <= 2, math.pi*times, math.pi*(4-times))
    angles = []
    for theta in phase:
        mask = np.zeros((180,180),np.uint8)
        polygon = cv2.boxPoints(((90,90),(100,10),math.degrees(theta))).round().astype(np.int32)
        cv2.fillPoly(mask,[polygon],255)
        a,b = mask_axis(mask)
        angles.append(math.atan2(*(b-a)[::-1]) % math.pi)
    result = summarize(times,angles)
    assert result['signed_net_turns'] == pytest.approx(0,abs=.005)
    assert result['raw_total_variation_turns'] == pytest.approx(2,abs=.02)
    assert result['physical_revolutions'] is None
