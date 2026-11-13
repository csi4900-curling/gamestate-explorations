"""Exercise the public replay entry point, source decoding and incomplete state."""
import json
import subprocess
import sys

import cv2
import numpy as np
import pytest

from prototype.detection_cache import digest


def write(path,value):
    path.write_text(json.dumps(value))


def test_public_post_throw_replay_preserves_missing_candidates_and_unknown_points(tmp_path):
    pytest.importorskip('ijson')
    run=tmp_path/'run';run.mkdir();motion=tmp_path/'motion';motion.mkdir()
    video=tmp_path/'source.mp4'
    writer=cv2.VideoWriter(str(video),cv2.VideoWriter_fourcc(*'mp4v'),30,(64,64))
    assert writer.isOpened()
    for i in range(30):writer.write(np.full((64,64,3),i*4,dtype=np.uint8))
    writer.release();source=digest(video)
    (run/'observations.jsonl').write_text('{}\n')
    write(run/'protocol.json',{'source_sha256':source,'sample_step_frames':3,'source_interval_s':[0,1],
                              'source_fps':30,'source_size_px':[64,64]})
    events=[{'candidate_id':'A','event_prediction':{'crossing_time_s':0},'segments':[
        {'role':'receiving','camera':'right_split','tracker_id':7,'pixel_points':[{'time_s':0}]}]},
        {'candidate_id':'B','event_prediction':{'crossing_time_s':.6},'segments':[]}]
    aggregate=tmp_path/'aggregate.json';write(aggregate,{'context':{'source_sha256':source},'events':events})
    colour=tmp_path/'colours.json';write(colour,{'source_sha256':source,'events':[{'event_id':'A','colour':'red'}]})
    stone={'tracker_id':54,'pixel':[40,30],'bbox_xyxy':[35,25,45,35],
           'confidence':.9,'height_adjusted_local_m':[0,0]}
    moved={**stone,'pixel':[20,20],'height_adjusted_local_m':[3,0]}
    (run/'match-observations.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in [
        {'frame_index':6,'time_s':.2,'boards':{'left':{'stones':[]},'right':{'stones':[stone]}}},
        {'frame_index':9,'time_s':.3,'boards':{'left':{'stones':[]},'right':{'stones':[moved]}}}]))
    write(motion/'manifest.json',{'source_sha256':source,'observations_sha256':digest(run/'observations.jsonl')})
    for panel in ['left','right']:
        np.savez(motion/(panel+'.npz'),frame_index=np.array([0,3,6]),time_s=np.array([0,.1,.2]),
                 track_id=np.array([7,7,7]),stationary=np.array([False,True,True]),
                 posterior_stationary=np.array([.1,.9,.9]))
    config=tmp_path/'config.json';write(config,{'group_to_team':{'red':'A','yellow':'B'},
         'house_radius_m':1.829,'stone_radius_m':.139,'duplicate_nms_iou':.7})
    output=tmp_path/'result'
    args=[sys.executable,'-m','prototype.scripts.finalize_full_match','--video',str(video),
          '--run-dir',str(run),'--output-dir',str(output),'--post-throw-config',str(config),
          '--post-throw-motion',str(motion),'--post-throw-aggregate',str(aggregate),
          '--event-colours',str(colour)]
    subprocess.run(args,capture_output=True,text=True,check=True)
    payload=json.loads((output/'states.json').read_text())
    assert payload['summary']['candidates']==2
    assert payload['summary']['snapshots']==1
    a,b=payload['events']
    assert a['snapshot_status']['frame_index']==6
    assert a['state']['boards']['right']['conditional_visible_board_points'] is None
    assert a['state']['boards']['right']['unobserved_previously_received_tracker_ids']==[7]
    assert a['state']['boards']['right']['post_throw_points'] is None
    assert b['proposal']['status']=='unresolved' and b['state'] is None
    assert all(r['physical_revolutions'] is None for r in payload['events'])
    assert (output/'index.html').exists() and (output/'states.js').exists()
    assert payload['timeline']['times']==[.2,.3]
    chunk=(output/'board-timeline/0.js').read_text()
    timeline=json.loads(chunk.removeprefix('window.receiveBoardState(0,').removesuffix(');\n'))
    assert timeline[0]['boards']['right']['stones'][0][1:5]==[40,30,0,0]
    assert timeline[1]['boards']['right']['stones'][0][1:5]==[20,20,3,0]
    assert timeline[1]['frame_index']==9
    # Existing output cannot be overwritten by a subsequent public launch.
    repeated=subprocess.run(args,capture_output=True,text=True)
    assert repeated.returncode!=0 and 'Preserve previous' in repeated.stderr
