"""Current observation-only app views over preserved completed-run evidence.

Rendering new HTML never reruns inference or edits a frozen result. Research
scores remain in the original data, outside the product's observation views.
"""
import hashlib
import html
import json
from pathlib import Path
import re


def trajectory_page(source,base_href):
    # Older frozen trajectory pages included an experimental match-state strip.
    text=source.read_text()
    text=re.sub(r' const st=stateAt\(t\);const stateBox=.*?(?= requestAnimationFrame\(draw\))','',text,flags=re.S)
    text=re.sub(r'<div id="state"[^>]*></div>','',text)
    return text.replace('<meta charset="utf-8">','<meta charset="utf-8"><base href="'+html.escape(base_href,quote=True)+'">',1)


def focused_views(app,job):
    if job.get('state')!='done':return job
    source=app.data/'jobs'/job['id']/'result'
    states=source/'boards/states.json'
    if job.get('imported') or not states.exists():
        job.update(presentation_supported=False,
                   presentation_message='This saved result has no supported observation view. Its original evidence is retained.')
        return job
    payload_bytes=states.read_bytes();payload=json.loads(payload_bytes)
    if not all(key in payload for key in ('events','timeline','dimensions','source_fps')):
        job.update(presentation_supported=False,
                   presentation_message='This older result has no supported observation view. Its original evidence is retained.')
        return job
    from prototype import post_throw_state
    from prototype.scripts import render_rink_viewer
    native_pages=[source/name/'index.html' for name in ('trajectories','camera-fragments')]
    version=hashlib.sha256(Path(__file__).read_bytes()+Path(post_throw_state.__file__).read_bytes()+Path(render_rink_viewer.__file__).read_bytes()+payload_bytes+
        b''.join(p.read_bytes() for p in native_pages if p.exists())).hexdigest()[:20]
    destination=app.data/'presentations'/job['id']/version
    with app.lock:
        if not (destination/'index.html').exists():
            board=destination/'boards';board.mkdir(parents=True,exist_ok=True)
            post_throw_state.render(board,Path(app.video(job['video_id'])['path']),payload,{},
                video_src='/media/'+job['video_id'],base_href=app.file_url(source/'boards')+'/',write_payload=False)
            for name,page in zip(('trajectories','camera-fragments'),native_pages):
                if page.exists():
                    target=destination/name;target.mkdir(exist_ok=True)
                    aggregate=source/('aggregate-rink.json' if name=='trajectories' else 'camera-fragments.json')
                    data=page.parent/'rink-data.js'
                    if aggregate.exists() and data.exists():
                        raw=data.read_text().split('=',1)[1].strip().rstrip(';')
                        current=json.loads(raw)
                        current['events']=[render_rink_viewer.compact_event(e) for e in json.loads(aggregate.read_text())['events']]
                        (target/'rink-data.js').write_text('window.RINK_DATA='+json.dumps(current,separators=(',',':')).replace('<','\\u003c')+';\n')
                        text=render_rink_viewer.TEMPLATE.replace('__DATA__',app.file_url(target/'rink-data.js')).replace('__VIDEO__','/media/'+job['video_id']).replace('__TITLE__','Trajectories — corrected development presentation')
                        text=text.replace('<meta charset="utf-8">','<meta charset="utf-8"><base href="'+html.escape(app.file_url(page.parent)+'/',quote=True)+'">',1)
                        (target/'index.html').write_text(text)
                    else:
                        (target/'index.html').write_text(trajectory_page(page,app.file_url(page.parent)+'/'))
            links=['<a href="boards/index.html" target="review">Stone observations</a>']
            if native_pages[0].exists():links.append('<a href="trajectories/index.html" target="review">Trajectories</a>')
            if native_pages[1].exists():links.append('<a href="camera-fragments/index.html" target="review">Unresolved camera tracks</a>')
            (destination/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>Video review</title>'
                '<style>body{font:16px system-ui;margin:20px;color:#203641}iframe{width:100%;height:85vh;border:1px solid #d5e1e4}</style>'
                '<h1>Video review</h1><p>Source detections and estimated positions. Calibration and tracking gaps remain visible.</p><p>'+
                ' · '.join(links)+'</p><iframe name="review" title="Synchronized observation review" src="boards/index.html"></iframe>')
    job.update(board_url=app.file_url(destination/'boards/index.html'),result_url=app.file_url(destination/'index.html'),
               trajectory_url=app.file_url(destination/'trajectories/index.html') if native_pages[0].exists() else None,
               presentation_supported=True,
               presentation_scope='Current observation-only presentation; original frozen outputs and observations retained.')
    return job
