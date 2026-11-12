import pytest
from prototype.stone_measurement import body_point_support


@pytest.mark.parametrize('box,boundary', [
    ([10, 0, 30, 20], 'source_top'),
    ([0, 10, 20, 30], 'source_left'),
    ([1900, 10, 1920, 30], 'source_right'),
    ([10, 1060, 30, 1080], 'source_bottom'),
    ([950, 10, 970, 30], 'split_panel_boundary'),
])
def test_censored_box_cannot_be_projected_as_full_stone_centre(box, boundary):
    record = {'bbox_xyxy':box}
    result=body_point_support(record,[1920,1080])
    assert not result['centre_supported']
    assert boundary in result['censored_boundaries']
    assert record == {'bbox_xyxy':box}


def test_small_unclipped_box_is_retained_without_video_specific_margin():
    assert body_point_support({'bbox_xyxy':[500,.01,530,20]},[1920,1080])['centre_supported']
