import cv2
import numpy as np
from prototype.spin.episodes import learned_scene_seeds


def test_learned_queries_keep_semantics_and_ambiguous_anchor(tmp_path):
    video=tmp_path/'scene.avi'
    w=cv2.VideoWriter(str(video),cv2.VideoWriter_fourcc(*'MJPG'),10,(64,48))
    w.write(np.zeros((48,64,3),np.uint8));w.release()
    class Detector:
        provenance={'model':'fixture'}
        def detect(self,frame):
            assert frame.shape==(48,64,3)
            return {'wall_seconds':.1,'detections':[
                {'pixel':[40,20],'bbox_xyxy':[35,15,45,25],'confidence':.8},
                {'pixel':[41,20],'bbox_xyxy':[36,15,46,25],'confidence':.7},
                {'pixel':[55,30],'bbox_xyxy':[50,25,60,35],'confidence':.9},
                {'pixel':[10,20],'bbox_xyxy':[5,15,15,25],'confidence':.9}]}
    seeds,diag=learned_scene_seeds(video,0,[40,20],[32,0,64,48],Detector())
    assert len(seeds)==1 and seeds[0]['pixel']==[55,30]
    assert seeds[0]['point_kind']=='body_box_center'
    assert seeds[0]['colour'] is None and not seeds[0]['physical_identity_verified']
    assert diag['event_query_support']=='ambiguous_boxes'
    assert diag['event_query_retained'] and not diag['physical_identity_verified']


def test_source_point_audit_keeps_hidden_and_does_not_interpolate():
    from prototype.scripts.audit_track_observations import audit
    result={'events':[{'segments':[{'status':'tracked','camera':'right_split','segment_id':'a',
        'times_s':[1.,2.], 'point_names':['a','b'], 'tracks_px':[[[330,5],[350,5]],[[330,5],[350,5]]],
        'point_visible':[[True,False],[True,True]]}]}]}
    protocol={'frames':[{'id':0,'time_s':1.},{'id':1,'time_s':1.5}]}
    annotations={'annotator':'fixture','rows':[{'frame_id':0,'boxes_xyxy':[[325,0,335,10]]},
                                             {'frame_id':1,'boxes_xyxy':[[325,0,335,10]]}]}
    r=audit(result,protocol,annotations)
    assert len(r['samples'])==2
    assert r['counts']['model_hidden']==1 and r['counts']['on_annotated_stone']==1
