import json
from pathlib import Path
from prototype.tests.test_workbench import app


def test_current_presentation_removes_experimental_views_without_editing_saved_run(app):
    asset=app.register_video(app.root/'video.mp4');identifier='012345abcdef'
    root=app.data/'jobs'/identifier;board=root/'result/boards';board.mkdir(parents=True)
    old_page=board/'index.html';old_page.write_text('<h1>Old experimental score</h1>')
    payload={'events':[{'event_id':'L1','crossing_time_s':.2,'proposal':{'status':'unresolved'}}],
        'dimensions':{'house_radius_m':1.829,'stone_radius_m':.139},'source_size_px':[64,64],'source_fps':30,
        'timeline':{'times':[.2],'chunk_size':256,'sample_step_s':.1,'source_interval_s':[0,1]},
        'detected_throw_scoring':{'history':[{'estimated_points':{'A':9}}]},'score_tracking':{'experimental':True}}
    states=board/'states.json';states.write_text(json.dumps(payload));(board/'states.js').write_text('window.POST_THROW='+json.dumps(payload)+';')
    row={'id':identifier,'state':'done','name':'Observed fixture','video_id':asset['id'],
         'source_sha256':asset['source_sha256'],'start_s':0,'end_s':1,'imported':False,
         'board_url':app.file_url(old_page)}
    job_file=root/'job.json';job_file.write_text(json.dumps(row))
    originals={p:p.read_bytes() for p in [states,old_page,job_file]}
    rendered=app.job(identifier)
    assert rendered['presentation_supported'] is True
    assert rendered['board_url']!=row['board_url']
    page=app.root/rendered['board_url'].removeprefix('/files/')
    text=page.read_text()
    assert '<base href="'+app.file_url(board)+'/' in text
    assert 'Stone observations' in text
    for removed in ['Detected throws · provisional points','reconstructed-score','scoreAt(', 'detectedScoreAt(', 'revolution']:
        assert removed not in text
    assert 'states.js' in text and 'board-timeline/' in text
    assert app.job(identifier)['board_url']==rendered['board_url']
    assert all(p.read_bytes()==before for p,before in originals.items())


def test_focused_views_prefers_throw_extent_aggregate_for_trajectories(app):
    asset=app.register_video(app.root/'video.mp4');identifier='abcdef012345'
    root=app.data/'jobs'/identifier;result=root/'result';board=result/'boards';traj=result/'trajectories'
    board.mkdir(parents=True);traj.mkdir(parents=True)
    payload={'events':[{'event_id':'L1','crossing_time_s':1.0,'proposal':{'status':'unresolved'}}],
        'dimensions':{'house_radius_m':1.829,'stone_radius_m':.139},'source_size_px':[64,64],'source_fps':30,
        'timeline':{'times':[1.0],'chunk_size':256,'sample_step_s':.1,'source_interval_s':[0,10]}}
    (board/'states.json').write_text(json.dumps(payload));(board/'states.js').write_text('window.POST_THROW='+json.dumps(payload)+';')
    def make_agg(end_t):
        pts=[{'time_s':t,'pixel':[10,10],'rink_position_m':[0,1],'rink_position_kind':'height_adjusted_estimate'} for t in [1.0,2.0,end_t]]
        return {'events':[{'candidate_id':'L1','event_prediction':{'crossing_time_s':1.0},
                           'throw_extent':{'status':'quiet_board_proposal','end_time_s':end_t},
                           'segments':[{'segment_id':'L1:receiving','role':'receiving','pixel_points':pts,'geometry_samples':pts}]}]}
    (result/'aggregate-rink.json').write_text(json.dumps(make_agg(9.0)))
    (result/'aggregate-rink-throw-extent.json').write_text(json.dumps(make_agg(3.0)))
    (traj/'index.html').write_text('<h1>Trajectories</h1>')
    (traj/'rink-data.js').write_text('window.RINK_DATA='+json.dumps({'events':[]})+';')
    (root/'job.json').write_text(json.dumps({'id':identifier,'state':'done','name':'Extent check','video_id':asset['id'],
        'source_sha256':asset['source_sha256'],'start_s':0,'end_s':10,'imported':False,'board_url':app.file_url(board/'index.html')}))
    rendered=app.job(identifier)
    data_text=(app.root/rendered['trajectory_url'].removeprefix('/files/')).with_name('rink-data.js').read_text()
    data=json.loads(data_text.split('=',1)[1].rstrip('; \n'))
    assert data['events'][0]['end_s']==3.0
    assert data['events'][0]['throw_extent']['end_time_s']==3.0
