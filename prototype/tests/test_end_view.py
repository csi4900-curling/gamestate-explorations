import cv2
import numpy as np
import json
from prototype.spin.end_view import export_end_views


def test_snapshot_uses_receiving_end_not_departure_or_visible_endpoint(tmp_path):
    video = tmp_path / 'source.avi'
    writer = cv2.VideoWriter(str(video), cv2.VideoWriter_fourcc(*'MJPG'), 10, (64, 48))
    for i in range(10):
        writer.write(np.full((48, 64, 3), i * 20, dtype=np.uint8))
    writer.release()
    event = {'candidate_id': 'test', 'segments': [
        {'segment_id': 'a', 'role': 'departure', 'status': 'tracked', 'times_s': [.9]},
        {'segment_id': 'b', 'role': 'receiving', 'status': 'tracked', 'times_s': [.2, .5],
         'point_visible': [[True], [False]]}]}
    row = export_end_views([event], video, tmp_path)[0]
    assert row['frame_index'] == 5 and row['time_s'] == .5
    assert row['settled'] is None
    assert row['segment_id'] == 'b'
    assert abs(cv2.imread(str(tmp_path / row['image'])).mean() - 100) < 3
    boards = {'left': {'stones': []}, 'right': {'stones': []}}
    path = tmp_path/'match-observations.jsonl'
    path.write_text(json.dumps({'frame_index': 5, 'time_s': .5, 'boards': boards})+'\n')
    row = export_end_views([event], video, tmp_path, observation_run=tmp_path)[0]
    assert row['both_panel_observations']['boards'] == boards
    assert row['both_panel_observations']['settled'] is None
    path.write_text(json.dumps({'frame_index': 4, 'time_s': .4, 'boards': boards})+'\n')
    row = export_end_views([event], video, tmp_path, observation_run=tmp_path)[0]
    assert row['both_panel_observations']['status'] == 'unavailable'


def test_missing_receiving_is_explicit(tmp_path):
    row = export_end_views([{'candidate_id': 'x', 'segments': []}], tmp_path/'missing.mp4', tmp_path)[0]
    assert row['status'] == 'unavailable'
    assert row['reason'] == 'No analyzed receiving frames'


def test_board_uses_current_registration_and_fresh_proposals(monkeypatch):
    from prototype.spin.end_view import project_board
    monkeypatch.setattr('prototype.right_large_cap_proposals.right_large_cap_proposals',
                        lambda frame: {'red': [{'pixel': [400, 200]}], 'yellow': []})
    segment = {'camera': 'right_split', 'projection': {
        'anchor_homography': [[.01, 0, -3], [0, .01, -2], [0, 0, 1]],
        'samples': [{'time_s': 5, 'registration': {
            'status': 'image_registered_house_projection',
            'reference_to_current': [[1, 0, 10], [0, 1, 0], [0, 0, 1]]}}]}}
    board = project_board(np.zeros((360, 640, 3), np.uint8), segment, 5)
    assert np.allclose(board['stones'][0]['position_m'], [.9, 0])
    assert board['stones'][0]['physical_identity'] is None
    assert board['complete_board'] is False and board['score'] is None
    assert board['new_calibration_fits'] == 0
    assert project_board(np.zeros((360,640,3), np.uint8), segment, 6)['status'] == 'unavailable'
    segment['projection']['samples'][0]['registration']['status'] = 'propagated_ring_inconsistency'
    assert project_board(np.zeros((360,640,3), np.uint8), segment, 5)['status'] == 'unavailable'


def test_board_height_recovers_known_elevated_cap(monkeypatch):
    from prototype.spin.end_view import project_board
    C = np.array([0.,12.,5.])
    R = np.array([[1,0,0],[0,5/13,-12/13],[0,-12/13,-5/13]])
    K = np.array([[600.,0,480],[0,600.,180],[0,0,1.]])
    P = K @ np.column_stack([R, -R @ C])
    H = np.linalg.inv(P[:,[0,1,3]])
    point = P @ np.array([.5,-.3,.136,1.])
    pixel = (point[:2]/point[2]).tolist()
    monkeypatch.setattr('prototype.right_large_cap_proposals.right_large_cap_proposals',
                        lambda frame: {'yellow': [{'pixel':pixel}]})
    segment = {'camera':'right_split','projection':{'anchor_homography':H.tolist(),
               'samples':[{'time_s':5,'registration':{'status':'existing_anchor_frame'}}]}}
    b = project_board(np.zeros((360,640,3),np.uint8), segment, 5)
    stone = b['stones'][0]
    assert np.allclose(stone['height_adjusted_position_m'], [.5,-.3], atol=1e-8)
    assert np.linalg.norm(np.array(stone['raw_position_m'])-[.5,-.3]) > .25


def test_learned_board_keeps_unknown_colour_and_body_height(monkeypatch):
    from prototype.spin.end_view import project_board
    C = np.array([0.,12.,5.]);R = np.array([[1,0,0],[0,5/13,-12/13],[0,-12/13,-5/13]])
    K = np.array([[600.,0,480],[0,600.,180],[0,0,1.]])
    P = K @ np.column_stack([R,-R@C]);H=np.linalg.inv(P[:,[0,1,3]])
    point=P@np.array([.5,-.3,.068,1.]);pixel=(point[:2]/point[2]).tolist()
    def forbidden(*args):raise AssertionError('Learned board must not call colour proposal detector')
    monkeypatch.setattr('prototype.right_large_cap_proposals.right_large_cap_proposals',forbidden)
    segment={'camera':'right_split','projection':{'anchor_homography':H.tolist(),
             'samples':[{'time_s':5,'registration':{'status':'existing_anchor_frame'}}]}}
    b=project_board(np.zeros((360,640,3),np.uint8),segment,5,
                    learned={'detections':[{'pixel':pixel,'confidence':.8}]})
    s=b['stones'][0]
    assert s['colour'] is None and s['physical_identity'] is None
    assert s['point_kind']=='body_box_center' and s['height_adjustment']['height_m']==.068
    assert np.allclose(s['height_adjusted_position_m'],[.5,-.3],atol=1e-8)


def test_custom_height_reaches_learned_board_geometry(monkeypatch):
    from prototype.spin.end_view import project_board
    C=np.array([0.,12.,5.]);R=np.array([[1,0,0],[0,5/13,-12/13],[0,-12/13,-5/13]])
    K=np.array([[600.,0,480],[0,600.,180],[0,0,1.]])
    P=K@np.column_stack([R,-R@C]);H=np.linalg.inv(P[:,[0,1,3]])
    point=P@np.array([.5,-.3,.09,1.]);pixel=(point[:2]/point[2]).tolist()
    segment={'camera':'right_split','projection':{'anchor_homography':H.tolist(),
             'feature_heights_m':{'body_box_center':.09},
             'samples':[{'time_s':5,'registration':{'status':'existing_anchor_frame'}}]}}
    b=project_board(np.zeros((360,640,3),np.uint8),segment,5,
                    learned={'detections':[{'pixel':pixel,'confidence':.8}]})
    assert b['stones'][0]['height_adjustment']['height_m']==.09
    assert np.allclose(b['stones'][0]['height_adjusted_position_m'],[.5,-.3],atol=1e-8)


def test_learned_colour_is_separate_evidence_for_both_saved_panels(tmp_path):
    video=tmp_path/'source.avi'
    writer=cv2.VideoWriter(str(video),cv2.VideoWriter_fourcc(*'MJPG'),10,(64,48))
    writer.write(np.zeros((48,64,3),np.uint8));writer.release()
    boards={panel:{'stones':[{'bbox_xyxy':box,'colour':None,'team':None,'physical_identity':None,'height_adjusted_local_m':[1.,2.]}]}
            for panel,box in [('left',[1,2,10,12]),('right',[35,2,45,12])]}
    path=tmp_path/'match-observations.jsonl'
    path.write_text(json.dumps({'frame_index':0,'time_s':0.,'boards':boards})+'\n')
    class Model:
        provenance={'fixture':True}
        def classify(self,frame,detections):
            return [{'prediction':'red' if d['bbox_xyxy'][0]<32 else 'yellow',
                     'status':'unverified_colour_ranking'} for d in detections]
    event={'candidate_id':'x','segments':[{'segment_id':'receive','role':'receiving','status':'tracked','times_s':[0.]}]}
    row=export_end_views([event],video,tmp_path,observation_run=tmp_path,stone_colour_model=Model())[0]
    observed=row['both_panel_observations']['boards']
    assert observed['left']['stones'][0]['colour_evidence']['prediction']=='red'
    assert observed['right']['stones'][0]['colour_evidence']['prediction']=='yellow'
    for panel in boards:
        actual=observed[panel]['stones'][0]
        assert {k:v for k,v in actual.items() if k!='colour_evidence'}==boards[panel]['stones'][0]
    assert json.loads(path.read_text())['boards']==boards
