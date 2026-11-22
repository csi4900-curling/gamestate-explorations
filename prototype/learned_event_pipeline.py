"""Shared learned-detection/ByteTrack line-event development mode.

Does not pass body-centre observations into the legacy cap-specific trajectory path.
"""
import hashlib,json,time,os
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import quote
import cv2
import numpy as np
from prototype.line_crossing_events import LineCrossings,validate_config
from prototype.stone_detector import StoneDetector


def _merge_windows(intervals, start_s, end_s):
    clipped = sorted((max(start_s, a), min(end_s, b)) for a, b in intervals if b > start_s and a < end_s)
    merged = []
    for a, b in clipped:
        if merged and a <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], b))
        else:
            merged.append((a, b))
    return merged


def _in_windows(time_s, windows):
    for a, b in windows:
        if a <= time_s <= b:
            return True
        if a > time_s:
            break
    return False


def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()


def run(video,output,config_path,checkpoint,*,start,end,source_id,match_state_config=None,detection_cache=None,detection_cache_prefix_samples=None,detector_backend='pytorch',detector_export=None,detector_head='checkpoint',detector_threads=4):
    from ultralytics.trackers.byte_tracker import BYTETracker
    from ultralytics.engine.results import Boxes
    from ultralytics.utils import YAML
    import ultralytics
    started=time.perf_counter();output=Path(output);config_path=Path(config_path)
    config=validate_config(json.loads(config_path.read_text()))
    source_hash=digest(video)
    if config.get('source_sha256',source_hash)!=source_hash:raise ValueError('Line configuration belongs to another source')
    if match_state_config is not None:
        match_cfg=json.loads(Path(match_state_config).read_text())
        if match_cfg.get('geometry_mode')=='explicit_source_calibration_v1':
            from prototype.rink_calibration import load_bundle
            if not match_cfg.get('source_calibration_bundle'):raise ValueError('Explicit source camera calibration required before analysis')
            load_bundle(Path(match_state_config).parent/match_cfg['source_calibration_bundle'],source_hash,[start,end])
    tracker_path=(config_path.parent/config['tracker_config']).resolve()
    tracker_settings=YAML.load(tracker_path)
    if tracker_settings.get('tracker_type')!='bytetrack':raise ValueError('This adapter supports upstream ByteTrack')
    if config['detector_confidence']>tracker_settings['track_low_thresh']:raise ValueError('Detector confidence must retain ByteTrack low-confidence association inputs')
    cap=cv2.VideoCapture(str(video));fps=cap.get(cv2.CAP_PROP_FPS);count=cap.get(cv2.CAP_PROP_FRAME_COUNT)
    if not cap.isOpened() or fps<=0 or not 0<=start<end<=count/fps:raise ValueError('Invalid source interval')
    if round(start*fps)>=round(end*fps):raise ValueError('Analysis interval must contain at least one source frame')
    if config['sample_hz']>fps:raise ValueError('sample_hz exceeds source frame rate')
    if output.exists():raise ValueError('Preserve previous output')
    output.mkdir(parents=True);(output/'config.json').write_text(json.dumps(config,indent=2))
    (output/'tracker.yaml').write_bytes(tracker_path.read_bytes())
    detector=StoneDetector(checkpoint,backend=detector_backend,export=detector_export,head=detector_head,threads=detector_threads);tracker=BYTETracker(SimpleNamespace(**tracker_settings));crossings=LineCrossings(config)
    step=max(1,round(fps/config['sample_hz']));first=round(start*fps);stop=round(end*fps)
    cap.set(cv2.CAP_PROP_POS_FRAMES,first);nframes=0;detection_s=association_s=0
    files=[Path(__file__),Path(__file__).with_name('line_crossing_events.py'),Path(__file__).with_name('stone_detector.py'),Path(__file__).with_name('detection_cache.py'),Path(__file__).parent/'scripts/run_throw_pipeline.py']
    (output/'code-snapshot').mkdir()
    for p in files:(output/'code-snapshot'/p.name).write_bytes(p.read_bytes())
    protocol={'status':'running','source_id':source_id,'source_sha256':source_hash,'source_interval_s':[start,end],
              'config_sha256':digest(config_path),'tracker_config':tracker_settings,'tracker_sha256':digest(tracker_path),
              'model':detector.provenance,'ultralytics':ultralytics.__version__,'code_sha256':{p.name:digest(p) for p in files},
              'sample_step_frames':step,'effective_sample_hz':fps/step,
              'source_fps':fps,'source_size_px':[int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))],
              'process_id':os.getpid(),'opencv':cv2.__version__,'opencv_build_sha256':hashlib.sha256(cv2.getBuildInformation().encode()).hexdigest(),
              'coverage_policy':'Every sampled source frame in requested interval. No legacy layout-window exclusion or surrounding-motion veto.',
              'line_placement':'User configured, fixed image coordinates; automatic line placement and camera-motion compensation not implemented.',
              'deduplication':'At most one crossing per tracker ID per line. ID fragmentation can duplicate physical events; different lines are separate observations, not merged throws.',
              'downstream':'Event-stage development output only; not attached to legacy cap-specific geometry or cross-view identity.'}
    cache=None
    if detection_cache is not None:
        from prototype.detection_cache import DetectionCache
        cache=DetectionCache(detection_cache,source_sha256=source_hash,model=detector.provenance,
                             confidence=config['detector_confidence'],decoder_sha256=protocol['opencv_build_sha256'],
                             prefix_samples=detection_cache_prefix_samples)
        protocol['detection_cache']=cache.provenance
    (output/'protocol.json').write_text(json.dumps(protocol,indent=2))
    observer=None
    aux_schedule_crossings=None
    if match_state_config is not None:
        from prototype.match_observation import MatchObserver
        observer=MatchObserver(match_state_config,output)
        for name in ('match_observation.py','scoreboard_observation.py'):
            p=Path(__file__).with_name(name)
            (output/'code-snapshot'/name).write_bytes(p.read_bytes())
        # Auto-project both calibrated hog lines for 5 Hz Pass 2 window scheduling
        # so fast throws on either panel never rely solely on the 1 Hz probe.
        if (observer.geometry is not None and hasattr(observer.geometry, 'bundle')
                and 'local_hog_y_m' in observer.config):
            aux_lines = []
            for asset in observer.geometry.bundle.get('calibrations', []):
                for panel_name, hog_y in observer.config['local_hog_y_m'].items():
                    rec = (asset.get('panels') or {}).get(panel_name)
                    if not rec or not rec.get('H_normalized_source_to_local_m'):
                        continue
                    try:
                        Hinv = np.linalg.inv(np.asarray(rec['H_normalized_source_to_local_m'], dtype=float))
                        raw_pts = []
                        for xm in (-2.375, 2.375):
                            v = Hinv @ np.array([xm, float(hog_y), 1.0], dtype=float)
                            if abs(v[2]) < 1e-12:
                                raise ValueError('singular')
                            raw_pts.append(((v[0] / v[2]) / 640.0, (v[1] / v[2]) / 360.0))
                        x_lo, x_hi = (0.0, 0.5) if panel_name == 'left' else (0.5, 1.0)
                        (x0, y0), (x1, y1) = sorted(raw_pts, key=lambda pt: pt[0])
                        if x1 < x_lo or x0 > x_hi:
                            continue
                        if x1 - x0 > 1e-12:
                            if x0 < x_lo:
                                y0 = y0 + (x_lo - x0) * (y1 - y0) / (x1 - x0)
                                x0 = x_lo
                            if x1 > x_hi:
                                y1 = y0 + (x_hi - x0) * (y1 - y0) / (x1 - x0)
                                x1 = x_hi
                        pts = [
                            [float(min(x_hi, max(x_lo, x0))), float(min(1.0, max(0.0, y0)))],
                            [float(min(x_hi, max(x_lo, x1))), float(min(1.0, max(0.0, y1)))],
                        ]
                        if pts[0] != pts[1]:
                            aux_lines.append({'id': f"sched_{asset.get('id', '0')}_{panel_name}",
                                              'endpoints_normalized': pts,
                                              'direction': 'both', 'deadband_normalized': 0})
                    except Exception:
                        continue
            if aux_lines:
                aux_schedule_crossings = LineCrossings({
                    'schema_version': 'stone-line-events-v1', 'sample_hz': config['sample_hz'],
                    'detector_confidence': config['detector_confidence'],
                    'tracker_config': config['tracker_config'], 'lines': aux_lines,
                })
    # Split two-pass execution: Pass 1 runs iGPU detection + ByteTrack + primary
    # line crossings with CPU idle; Pass 2 runs CPU camera geometry + OCR with
    # iGPU idle (avoids shared-TDP throttling on integrated GPUs and enables
    # verified scheduled geometry).
    try:
        with (output/'observations.jsonl').open('w') as f:
            for frame_index in range(first,stop):
                if not cap.grab():raise RuntimeError(f'Decode failed at frame {frame_index}')
                if (frame_index-first)%step:continue
                ok,frame=cap.retrieve()
                if not ok:raise RuntimeError('Frame retrieval failed')
                if round(cap.get(cv2.CAP_PROP_POS_FRAMES))-1!=frame_index:raise RuntimeError('Source frame seek mismatch')
                if nframes==0:cv2.imwrite(str(output/'line-preview.jpg'),frame)
                prediction=cache.get(frame_index) if cache is not None else None
                if prediction is None:prediction=detector.detect(frame,confidence=config['detector_confidence'])
                detection_s+=prediction['wall_seconds']
                boxes=np.asarray([[*d['bbox_xyxy'],d['confidence'],d['class_id']] for d in prediction['detections']],dtype=np.float32).reshape(-1,6)
                t=time.perf_counter();tracks=tracker.update(Boxes(boxes,frame.shape[:2]));association_s+=time.perf_counter()-t
                observations=[]
                for tr in tracks:
                    index=int(tr[-1]);d=prediction['detections'][index];x,y=d['pixel']
                    observations.append({'track_id':int(tr[4]),'point_normalized':[x/frame.shape[1],y/frame.shape[0]],
                                         'pixel':[x,y],'bbox_xyxy':d['bbox_xyxy'],'confidence':d['confidence'],'detection_index':index})
                now=frame_index/fps;crossings.update(observations,now)
                if aux_schedule_crossings is not None:aux_schedule_crossings.update(observations,now)
                row={'time_s':now,'frame_index':frame_index,'detections':prediction['detections'],'tracked_observations':observations,
                     'detector_wall_seconds':prediction['wall_seconds'],'upstream_speed_ms':prediction['upstream_speed_ms'],
                     'detection_reused':prediction.get('reused_from_cache',False),
                     'prior_detector_wall_seconds':prediction.get('prior_detector_wall_seconds')}
                f.write(json.dumps(row)+'\n')
                nframes+=1
                if nframes%25==0:
                    f.flush()
                    progress={'status':'running','phase':'detection','samples':nframes,'source_time_s':now,'crossings':len(crossings.events),
                              'wall_seconds':time.perf_counter()-started,'detector_seconds':detection_s,'events_so_far':crossings.events}
                    pending=output/'progress.pending.json';pending.write_text(json.dumps(progress));pending.replace(output/'progress.json')
                    print(json.dumps({k:v for k,v in progress.items() if k!='events_so_far'}),flush=True)
            f.flush()
        cap.release()
        if observer is not None:
            source_size_px = tuple(protocol['source_size_px'])
            sched = observer.config.get('geometry_schedule')
            use_schedule = isinstance(sched, dict) and sched.get('mode') == 'two_pass_probe_v1' and 'local_hog_y_m' in observer.config
            probe_cache = {}
            windows = None
            if use_schedule:
                from prototype.directional_handoff import metric_crossings
                probe_hz = float(sched.get('probe_hz', 1.0))
                before_s = float(sched.get('before_s', 12.0))
                primary_before_s = float(sched.get('primary_before_s', max(before_s, 16.0)))
                after_s = float(sched.get('after_s', 35.0))
                probe_stride = max(1, round(protocol['effective_sample_hz'] / probe_hz))
                aux_windows = ([(e['crossing_time_s'] - before_s, e['crossing_time_s'] + after_s)
                                for e in aux_schedule_crossings.events]
                               if aux_schedule_crossings is not None else [])
                windows = _merge_windows([(e['crossing_time_s'] - primary_before_s, e['crossing_time_s'] + after_s)
                                          for e in crossings.events] + aux_windows, start, end)
                # Sub-pass 2a: uninterrupted coarse probe across both panels to detect
                # arrival-only or reverse-direction metric crossings outside primary windows.
                cap_probe = cv2.VideoCapture(str(video))
                cap_probe.set(cv2.CAP_PROP_POS_FRAMES, first)
                probe_states = []
                try:
                    with (output/'observations.jsonl').open() as obs_in:
                        sample_idx = 0
                        next_row = json.loads(obs_in.readline()) if nframes else None
                        for frame_index in range(first, stop):
                            if not cap_probe.grab():
                                raise RuntimeError(f'Decode failed during geometry probe at frame {frame_index}')
                            if next_row is None or frame_index != next_row['frame_index']:
                                continue
                            if sample_idx % probe_stride == 0:
                                ok, frame = cap_probe.retrieve()
                                if not ok:
                                    raise RuntimeError('Frame retrieval failed during geometry probe')
                                state = observer.observe(frame, next_row, write_stream=False, run_ocr=False)
                                probe_cache[frame_index] = state
                                probe_states.append(state)
                            sample_idx += 1
                            line = obs_in.readline()
                            next_row = json.loads(line) if line else None
                finally:
                    cap_probe.release()
                if probe_states:
                    probe_crossings = metric_crossings(
                        probe_states,
                        hog_y_by_panel=observer.config['local_hog_y_m'],
                        max_geometry_gap_s=max(1.5, 2.5 / max(probe_hz, 0.1)),
                    )
                    probe_states.clear()
                    windows = _merge_windows(
                        windows + [(c['crossing_time_s'] - before_s, c['crossing_time_s'] + after_s) for c in probe_crossings],
                        start, end)
            # Sub-pass 2b: single sequential pass writing chronological match-observations.jsonl.
            cap_geo = cv2.VideoCapture(str(video))
            cap_geo.set(cv2.CAP_PROP_POS_FRAMES, first)
            geo_done = 0
            try:
                with (output/'observations.jsonl').open() as obs_in:
                    line = obs_in.readline()
                    next_row = json.loads(line) if line else None
                    for frame_index in range(first, stop):
                        if not cap_geo.grab():
                            raise RuntimeError(f'Decode failed during geometry pass at frame {frame_index}')
                        if next_row is None or frame_index != next_row['frame_index']:
                            continue
                        now = next_row['time_s']
                        ocr_due = observer.next_score is None or now + 1e-8 >= observer.next_score
                        if frame_index in probe_cache:
                            cached_state = probe_cache.pop(frame_index)
                            ocr_frame = None
                            if ocr_due:
                                ok, ocr_frame = cap_geo.retrieve()
                                if not ok:
                                    raise RuntimeError('Frame retrieval failed during OCR')
                            observer.write_state(cached_state, frame=ocr_frame)
                        elif (not use_schedule) or _in_windows(now, windows):
                            ok, frame = cap_geo.retrieve()
                            if not ok:
                                raise RuntimeError('Frame retrieval failed during geometry pass')
                            observer.observe(frame, next_row)
                        else:
                            ocr_frame = None
                            if ocr_due:
                                ok, ocr_frame = cap_geo.retrieve()
                                if not ok:
                                    raise RuntimeError('Frame retrieval failed during OCR')
                            observer.observe_skipped(next_row, source_size_px, frame=ocr_frame)
                        geo_done += 1
                        if geo_done % 25 == 0:
                            progress = {'status': 'running', 'phase': 'geometry', 'samples': geo_done, 'total_samples': nframes,
                                        'source_time_s': now, 'crossings': len(crossings.events),
                                        'wall_seconds': time.perf_counter() - started, 'detector_seconds': detection_s,
                                        'geometry_seconds': observer.geometry_s, 'events_so_far': crossings.events}
                            pending = output / 'progress.pending.json'
                            pending.write_text(json.dumps(progress))
                            pending.replace(output / 'progress.json')
                            print(json.dumps({k: v for k, v in progress.items() if k != 'events_so_far'}), flush=True)
                        line = obs_in.readline()
                        next_row = json.loads(line) if line else None
            finally:
                cap_geo.release()
    except Exception as exc:
        (output/'failure.json').write_text(json.dumps({'status':'failed','error':f'{type(exc).__name__}: {exc}',
            'sampled_frames':nframes,'events_so_far':crossings.events,'wall_seconds':time.perf_counter()-started},indent=2))
        raise
    finally:
        cap.release()
        if observer is not None:observer.close()
        if cache is not None:cache.close()
    result={**protocol,'status':'development_complete_event_stage','events':crossings.events,'sampled_frames':nframes,
            'wall_seconds':time.perf_counter()-started,'detector_seconds':detection_s,'association_seconds':association_s,
            'reused_detector_frames':cache.reused if cache is not None else 0,
            'prior_detector_seconds_for_reused_frames':cache.prior_detector_seconds if cache is not None else 0.,
            'limitations':['Stone crossings are not yet verified live deliveries. Clearing, replay and collisions can cross a line.',
                           'Tracker IDs are not physical identities. Missing observations break crossing evidence.',
                           'No colour gate, surrounding-motion veto, minimum speed/span gate or cross-track time suppression is applied.']}
    (output/'events.json').write_text(json.dumps(result,indent=2))
    render(result,config,video,output)
    return result


def render(result,config,video,output):
    data=json.dumps({'result':result,'config':config}).replace('<','\\u003c')
    url=quote(os.path.relpath(Path(video).resolve(),output.resolve()))
    (output/'index.html').write_text(TEMPLATE.replace('__DATA__',data).replace('__VIDEO__',url))


TEMPLATE='''<!doctype html><meta charset="utf-8"><title>Learned stone line crossings</title>
<style>body{font:17px system-ui;max-width:1100px;margin:25px auto}#source{position:relative}video,canvas{width:100%}canvas{position:absolute;left:0;top:0;pointer-events:none}button,select{padding:8px;margin:6px}p{line-height:1.5}</style>
<h1>Learned stone crossings — development</h1><p>Learned detector + upstream ByteTrack. Configured line; no surrounding-motion rejection. Crossings are candidates, not verified throws or physical identities. No trajectory attachment in this event-stage mode.</p>
<select id="events"></select><button id="play">Play crossing evidence</button><p id="status"></p>
<div id="source"><video id="video" controls src="__VIDEO__"></video><canvas id="overlay"></canvas></div>
<p>Green line: configured gate. Orange markers: the two observed detection centres bracketing the selected crossing. Crossing time is interpolated, not exact release. Line direction is defined by endpoint order; for a left-to-right horizontal line, positive is downward.</p>
<a href="config.json">Resolved configuration</a> · <a href="events.json">Events and provenance</a> · <a href="observations.jsonl">All sampled observations</a>
<script>const D=__DATA__,v=document.querySelector('#video'),c=document.querySelector('#overlay'),sel=document.querySelector('#events');let stop=null;
D.result.events.forEach((e,i)=>{const o=document.createElement('option');o.value=i;o.textContent=e.id+' · '+e.line_id+' · '+e.direction+' · '+e.crossing_time_s.toFixed(3)+' s';sel.append(o)});
function draw(){c.width=v.videoWidth;c.height=v.videoHeight;const x=c.getContext('2d');x.strokeStyle='#00e663';x.lineWidth=3;for(const l of D.config.lines){x.beginPath();l.endpoints_normalized.forEach((p,i)=>x[i?'lineTo':'moveTo'](p[0]*c.width,p[1]*c.height));x.stroke()}const e=D.result.events[Number(sel.value)];if(e){x.strokeStyle='#ff981a';for(const o of e.observations){x.beginPath();x.arc(o.point_normalized[0]*c.width,o.point_normalized[1]*c.height,6,0,Math.PI*2);x.stroke()}}document.querySelector('#status').textContent=D.result.events.length+' crossings · source '+v.currentTime.toFixed(3)+' s';if(stop!==null&&v.currentTime>=stop){v.pause();stop=null}requestAnimationFrame(draw)}
function choose(){stop=null;v.pause();v.currentTime=D.result.events[Number(sel.value)]?.crossing_time_s??D.result.source_interval_s[0]}
sel.onchange=choose;document.querySelector('#play').onclick=()=>{const e=D.result.events[Number(sel.value)];if(!e)return;v.currentTime=Math.max(D.result.source_interval_s[0],e.observed_bracket_s[0]-1);stop=Math.min(D.result.source_interval_s[1],e.observed_bracket_s[1]+1);v.play()};document.querySelector('#play').disabled=!D.result.events.length;v.addEventListener('loadedmetadata',choose);if(v.readyState>=1)choose();requestAnimationFrame(draw);</script>'''
