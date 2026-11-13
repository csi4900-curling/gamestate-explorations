import pytest

from prototype.saved_board_geometry import replay, replay_observations


def board(centres):
    return {'homography_normalized_pixels_to_local_metres': [[1,0,0],[0,1,0],[0,0,1]],
            'stones': [{'height_correction': {'camera': {'camera_centre_m': c}}} for c in centres]}


def test_replay_height_and_source_scaling():
    r = replay(board([[0,0,10]]), [[6,12]], [1920,1080], height_m=1)[0]
    assert r['ice_plane_local_m'] == [2,4]
    assert r['height_adjusted_local_m'] == pytest.approx([1.8,3.6])


def test_missing_geometry_does_not_invent_camera():
    assert replay(board([]), [[2,4]], [640,360], height_m=.1)[0]['height_adjusted_local_m'] is None
    assert replay({}, [[2,4]], [640,360], height_m=.1)[0]['ice_plane_local_m'] is None


def test_conflicting_priors_are_not_chosen_arbitrarily():
    with pytest.raises(ValueError, match='Conflicting'):
        replay(board([[0,0,10],[0,1,10]]), [[2,4]], [640,360], height_m=.1)


def test_join_preserves_missing_height_and_tracker_provenance():
    geometry = {'frame_index': 3, 'time_s': .1, 'boards': {'left': board([]), 'right': board([])}}
    observations = {'frame_index': 3, 'time_s': .1, 'detections': [{'pixel': [2,4]}],
                    'tracked_observations': [{'detection_index': 0, 'track_id': 7}]}
    r = next(replay_observations([observations], [geometry], [640,360], .068))
    stone = r['boards']['left']['stones'][0]
    assert stone['tracker_id'] == 7
    assert stone['physical_identity'] is None
    assert stone['height_adjusted_local_m'] is None
    assert r['boards']['right']['stones'] == []


@pytest.mark.parametrize('frame,t', [(2,.1),(3,.2)])
def test_join_rejects_wrong_frame_or_timestamp(frame,t):
    geometry = {'frame_index': frame, 'time_s': t}
    observations = {'frame_index': 3, 'time_s': .1}
    with pytest.raises(ValueError, match='exact source-frame'):
        list(replay_observations([observations], [geometry], [640,360], .068))
