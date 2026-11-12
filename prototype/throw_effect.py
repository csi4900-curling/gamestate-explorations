"""Per-throw board change from saved public-pipeline observations.

Replays existing tracker observations and post-throw proposals; it does not
rerun detection, tracking or geometry. For each event candidate it compares the
receiving-panel stones before the delivered stone arrives with those in the
proposed low-motion interval, and keeps the observed paths of stones that moved.
Positions inherit unverified calibration. A tracker ID is not physical identity;
only stationary stones are re-linked, by the physical exclusion of two stone
centres within one radius. Collision identity through an ID change stays open.
"""
import html
import json
import math
import os
from pathlib import Path
from statistics import median

from prototype.detection_cache import digest
from prototype.house_points import points_lying

DEFAULTS = {
    'before_window_s': 2.0,
    'before_guard_s': 0.1,
    'minimum_window_samples': 3,
    'moved_minimum_m': 0.05,
    'moved_scatter_factor': 3.0,
    'sheet_half_width_m': 2.375,
    'quiet_window_s': 2.0,
    'quiet_search_step_s': 0.5,
    'provenance': 'Engineering defaults for a development replay; not validated thresholds.',
}


def load_tracks(path):
    """Receiving observations by panel and tracker: [(time_s, position or None)]."""
    tracks = {}
    with Path(path).open() as stream:
        for line in stream:
            row = json.loads(line)
            for panel, board in row['boards'].items():
                for stone in board['stones']:
                    if stone.get('tracker_id') is None:
                        continue
                    tracks.setdefault(panel, {}).setdefault(stone['tracker_id'], []).append(
                        (row['time_s'], stone.get('height_adjusted_local_m')))
    return tracks


def window(samples, start, end, minimum):
    """Median position and scatter in a closed interval; None if unsupported."""
    points = [p for t, p in samples if start <= t <= end and p is not None]
    if len(points) < minimum:
        return None
    centre = [median(p[0] for p in points), median(p[1] for p in points)]
    return {'position_m': centre, 'samples': len(points),
            'scatter_m': median(math.dist(p, centre) for p in points)}


def path(samples, start, end):
    """Observed samples only; missing geometry stays an explicit gap."""
    return [[t, *(p or [None, None])] for t, p in samples if start <= t <= end]


def colour_at(evidence, tracker_id, time_s, *, not_after=False):
    """Colour of the sample nearest in time; a track whose samples differ may have switched stones.

    With not_after, samples up to time_s are preferred: a stone already resting
    on the board is identified before the delivered stone reaches it, and a later
    sample can come from a collision crop or a tracker that changed stones.
    """
    samples = [r for r in (evidence or {}).get(str(tracker_id), {}).get('samples', []) if r.get('prediction')]
    if not samples:
        return None, None
    earlier = [r for r in samples if r['time_s'] <= time_s] if not_after else []
    nearest = min(earlier or samples, key=lambda r: abs(r['time_s']-time_s))
    return nearest['prediction'], len({r['prediction'] for r in samples}) > 1


def in_play(position, hog_y_m, *, half_width_m, house_radius_m, stone_radius_m):
    # Centre between the hog line and a stone fully past the back line; stored
    # stones and far projections stay in the record but outside the board.
    along = position[1]*math.copysign(1., hog_y_m)
    return abs(position[0]) <= half_width_m and -(house_radius_m+stone_radius_m) <= along <= abs(hog_y_m)


def quiet_interval(panel_tracks, delivered, start, end, region, settings):
    """Earliest window in which no in-play stone shows net displacement.

    The saved motion posterior alternates on pixel jitter for resting stones, and
    the longest low-motion run can fall during later handling. Here each track's
    half-window medians are compared; later clearing cannot move the choice
    earlier. An unobserved delivered stone that reappears in play later blocks
    the window instead of being assumed at rest.
    """
    span, minimum = settings['quiet_window_s'], settings['minimum_window_samples']
    last_delivered = max((t for t, p in panel_tracks[delivered] if p is not None and region(p)), default=None)
    t = start
    while t+span <= end:
        quiet = True
        for tracker_id, samples in panel_tracks.items():
            a = window(samples, t, t+span/2, minimum)
            b = window(samples, t+span/2, t+span, minimum)
            if a is None or b is None:
                if tracker_id == delivered and last_delivered is not None and last_delivered > t:
                    quiet = False; break
                continue
            # The delivered stone counts wherever it is: it arrives from outside the region.
            if ((tracker_id == delivered or region(a['position_m']) or region(b['position_m'])) and
                    math.dist(a['position_m'], b['position_m']) > settings['moved_minimum_m']):
                quiet = False; break
        if quiet:
            return [t, t+span]
        t += settings['quiet_search_step_s']
    return None


def effect(record, tracks, *, house_radius_m, stone_radius_m, hog_y_by_panel, settings, search_end_s,
           colours=None, groups=None):
    proposal = record['proposal']
    base = {'event_id': record['event_id'], 'crossing_time_s': record['crossing_time_s']}
    if 'time_s' not in proposal:
        return {**base, 'status': 'unresolved', 'reason': proposal.get('reason')}
    panel, delivered = proposal['panel'], proposal['receiving_tracker_id']
    panel_tracks = tracks.get(panel, {})
    if delivered not in panel_tracks:
        return {**base, 'status': 'unresolved', 'reason': 'delivered_track_missing_from_observations'}
    arrival = panel_tracks[delivered][0][0]
    def region(position):
        return in_play(position, hog_y_by_panel[panel], half_width_m=settings['sheet_half_width_m'],
                       house_radius_m=house_radius_m, stone_radius_m=stone_radius_m)

    settle = quiet_interval(panel_tracks, delivered, arrival, search_end_s, region, settings)
    if settle is None:
        return {**base, 'status': 'unresolved', 'reason': 'no_quiet_board_interval_before_next_candidate',
                'panel': panel, 'delivered_tracker_id': delivered, 'arrival_time_s': arrival}
    minimum = settings['minimum_window_samples']
    before = {}; after = {}
    for tracker_id, samples in panel_tracks.items():
        if tracker_id != delivered:
            found = window(samples, arrival-settings['before_window_s'],
                           arrival-settings['before_guard_s'], minimum)
            if found: before[tracker_id] = found
        found = window(samples, settle[0], settle[1], minimum)
        if found: after[tracker_id] = found
    links = {k: (k, 'same_tracker') for k in before if k in after}
    # Two distinct stone centres cannot lie within one stone radius of each other.
    free = [k for k in after if k not in before and k != delivered]
    for old in sorted(set(before)-set(links)):
        near = [k for k in free if math.dist(before[old]['position_m'], after[k]['position_m']) < stone_radius_m]
        if len(near) == 1:
            links[old] = (near[0], 'stationary_position'); free.remove(near[0])

    def house(position):
        return max(0., math.hypot(*position)-stone_radius_m) <= house_radius_m


    def row(old, new, link):
        b, a = before.get(old), after.get(new)
        distance = math.dist(b['position_m'], a['position_m']) if b and a else None
        noise = max(b['scatter_m'], a['scatter_m']) if b and a else None
        middle = (settle[0]+settle[1])/2
        if b:
            colour, switched = colour_at(colours, old, arrival, not_after=True)
            later = colour_at(colours, new, middle)[0] if a else None
        else:
            colour, switched = colour_at(colours, new, middle)
            later = None
        change = ('delivered' if new == delivered and old is None else
                  'left_view_or_lost' if a is None else 'appeared_unexplained' if b is None else
                  'moved' if distance > max(settings['moved_minimum_m'], settings['moved_scatter_factor']*noise)
                  else 'unchanged')
        return {'before_tracker_id': old, 'after_tracker_id': new, 'link': link, 'change': change,
                'before_m': b and b['position_m'], 'after_m': a and a['position_m'],
                'displacement_m': distance, 'window_scatter_m': noise,
                'touches_house_before': b and house(b['position_m']),
                'touches_house_after': a and house(a['position_m']),
                'in_play_before': b and region(b['position_m']),
                'in_play_after': a and region(a['position_m']),
                'colour': colour,
                'colour_basis': 'last_track_sample_before_arrival' if b else 'track_sample_nearest_settled_board',
                'colour_differs_after_throw': bool(colour and later and later != colour),
                'colour_differs_along_track': switched,
                'physical_identity_verified': False}

    stones = [row(old, *links.get(old, (None, None))) for old in sorted(before)]
    stones += [row(None, new, None) for new in sorted(set(after)-{v[0] for v in links.values()})]
    moving = {s['before_tracker_id'] if s['before_tracker_id'] is not None else s['after_tracker_id']
              for s in stones if s['change'] != 'unchanged'}
    board = [{'observation_id': s['after_tracker_id'], 'position_m': s['after_m'], 'group': s['colour']}
             for s in stones if s['in_play_after']]
    points = points_lying(board, house_radius_m=house_radius_m, stone_radius_m=stone_radius_m,
                          groups=groups) if groups else None
    for s in stones:
        if s['change'] == 'moved' and s['after_tracker_id'] != s['before_tracker_id']:
            moving.add(s['after_tracker_id'])
    return {**base, 'status': 'review_proposal', 'panel': panel, 'delivered_tracker_id': delivered,
            'arrival_time_s': arrival, 'settle_interval_s': settle, 'stones': stones,
            'paths': {str(k): path(panel_tracks[k], arrival-settings['before_window_s'], settle[1])
                      for k in sorted(moving)},
            'counts': {k: sum(s['change'] == k for s in stones) for k in
                       ['delivered', 'moved', 'unchanged', 'left_view_or_lost', 'appeared_unexplained']},
            'in_play': {'before': sum(bool(s['in_play_before']) for s in stones),
                        'after': sum(bool(s['in_play_after']) for s in stones),
                        'changed': sum(s['change'] != 'unchanged' and bool(s['in_play_before'] or s['in_play_after'])
                                       for s in stones)},
            'points_lying_after': points and {k: points[k] for k in
                                               ['conditional_points_by_group', 'unresolved_observations', 'status']},
            'settle_selection': 'Earliest window with no net in-play stone displacement after arrival.',
            'superseded_motion_proposal_interval_s': proposal['stationary_interval_s'],
            'tracks_with_inconsistent_colour': [s['after_tracker_id'] if s['after_tracker_id'] is not None
                                           else s['before_tracker_id'] for s in stones
                                           if s['colour_differs_along_track']],
            'limitations': ['Quiet-window proposal is not a verified settled board.',
                            'A stone whose tracker ID changes while moving appears as lost plus appeared.',
                            'Positions inherit unverified calibration; displacement is not a validated measurement.']}


VIEWER = '''<!doctype html><html lang="en"><meta charset="utf-8">
<title>Throws</title>
<style>body{font:16px system-ui;margin:24px;color:#233746}select,button{font:inherit;padding:8px}
video{width:100%;display:block}main{max-width:1440px}.views{display:grid;grid-template-columns:2fr 1fr;gap:16px}
canvas{width:100%;background:#f4f8fa}.note{background:#fff5d9;padding:12px}table{border-collapse:collapse;font-size:14px}
td,th{padding:3px 8px;text-align:left;border-bottom:1px solid #d5e1e4}#points{font-size:20px;font-weight:600}</style><main>
<h1>Throws</h1>
<p class="note">Each throw: receiving-house stones before the delivered stone arrives, observed paths of stones that moved, and the board in the first quiet interval afterwards. Positions depend on calibration; tracker IDs are provisional and the quiet interval is a proposal.</p>
<select id="pick" aria-label="Throw"></select> <button id="play">Play throw</button> <button id="after">Go to board after</button>
<div class="views"><div><video id="video" controls preload="metadata" src="VIDEO_URL"></video>
<p id="status"></p><p id="points"></p><table id="changes"></table></div>
<div><canvas id="rink" width="420" height="720"></canvas>
<p>Hollow dashed = position before · filled = after · line = observed path · faded = out of play · grey = colour unavailable</p></div></div>
</main><script src="effects.js"></script><script>
const D=window.THROW_EFFECTS,pick=document.querySelector('#pick'),video=document.querySelector('#video');
const canvas=document.querySelector('#rink'),ctx=canvas.getContext('2d'),S=64,dim=D.dimensions;
const fill={red:'#c23e40',yellow:'#caa820'};let stopAt=null;
for(const e of D.events){const o=document.createElement('option');o.value=pick.length;
 o.textContent=e.event_id+' · '+e.crossing_time_s.toFixed(1)+' s'+(e.status==='unresolved'?' · unresolved':'');pick.append(o)}
const current=()=>D.events[Number(pick.value)];
function frame(e){const hog=dim.hog_y_by_panel_m[e.panel],lo=Math.min(hog,-Math.sign(hog)*(dim.house_radius_m+0.6));
 const top=Math.min(lo,hog)-0.3;return{hog,px:p=>[canvas.width/2+p[0]*S,30+(p[1]-top)*S]}}
function stone(f,p,colour,style){const [x,y]=f.px(p);ctx.beginPath();ctx.arc(x,y,dim.stone_radius_m*S,0,Math.PI*2);
 ctx.globalAlpha=style.alpha??1;ctx.setLineDash(style.dash||[]);ctx.lineWidth=2;ctx.strokeStyle=fill[colour]||'#777';ctx.fillStyle=ctx.strokeStyle;
 if(style.hollow)ctx.stroke();else ctx.fill();ctx.setLineDash([]);ctx.globalAlpha=1}
function draw(t){const e=current();ctx.clearRect(0,0,canvas.width,canvas.height);if(e.status==='unresolved')return;
 const f=frame(e),w=dim.sheet_half_width_m,back=-Math.sign(f.hog)*dim.house_radius_m;ctx.lineWidth=1;ctx.strokeStyle='#9bb7c2';
 const [x0,y0]=f.px([-w,Math.min(f.hog,back)]),[x1,y1]=f.px([w,Math.max(f.hog,back)]);ctx.strokeRect(x0,y0,x1-x0,y1-y0);
 for(const k of [1,2/3,1/3]){const [x,y]=f.px([0,0]);ctx.beginPath();ctx.arc(x,y,dim.house_radius_m*k*S,0,Math.PI*2);ctx.stroke()}
 for(const y of [0,f.hog]){const a=f.px([-w,y]),b=f.px([w,y]);ctx.beginPath();ctx.moveTo(...a);ctx.lineTo(...b);ctx.stroke()}
 ctx.fillStyle='#233746';ctx.font='13px system-ui';ctx.fillText('hog line',f.px([-w,f.hog])[0]+4,f.px([-w,f.hog])[1]-4);
 const colourOf={};for(const s of e.stones){for(const k of [s.before_tracker_id,s.after_tracker_id])if(k!==null)colourOf[k]=s.colour}
 for(const [id,rows] of Object.entries(e.paths)){ctx.strokeStyle=fill[colourOf[id]]||'#777';ctx.lineWidth=2;let last=null;ctx.beginPath();
  for(const [time,x,y] of rows){if(x===null){last=null;continue}const p=f.px([x,y]);
   if(last!==null&&time-last<0.25)ctx.lineTo(...p);else ctx.moveTo(...p);last=time}ctx.stroke()}
 for(const s of e.stones){if(s.change!=='unchanged'&&s.before_m)stone(f,s.before_m,s.colour,{hollow:true,dash:[4,3]});
  if(s.after_m)stone(f,s.after_m,s.colour,{alpha:s.in_play_after?1:0.3})}
 if(t!==null&&t>=e.arrival_time_s-2.1&&t<=e.settle_interval_s[1])for(const [id,rows] of Object.entries(e.paths)){
  let best=null;for(const r of rows)if(r[1]!==null&&Math.abs(r[0]-t)<0.15&&(!best||Math.abs(r[0]-t)<Math.abs(best[0]-t)))best=r;
  if(best){const [x,y]=f.px([best[1],best[2]]);ctx.beginPath();ctx.arc(x,y,dim.stone_radius_m*S+4,0,Math.PI*2);ctx.lineWidth=3;ctx.strokeStyle='#0a84a8';ctx.stroke()}}}
function show(seek=true){const e=current(),status=document.querySelector('#status'),points=document.querySelector('#points'),table=document.querySelector('#changes');
 table.innerHTML='';points.textContent='';stopAt=null;
 if(e.status==='unresolved'){status.textContent='No board change available: '+e.reason+'.';if(seek)video.currentTime=e.crossing_time_s;draw(null);return}
 status.textContent='Arrives '+e.arrival_time_s.toFixed(1)+' s · board after '+e.settle_interval_s[0].toFixed(1)+'–'+e.settle_interval_s[1].toFixed(1)+' s · in play '+e.in_play.before+' → '+e.in_play.after+
  (e.tracks_with_inconsistent_colour.length?' · colour not consistent along track '+e.tracks_with_inconsistent_colour.join(', ')+' (identity may switch at some point)':'');
 const p=e.points_lying_after;if(p)points.textContent=p.conditional_points_by_group?Object.entries(p.conditional_points_by_group).map(([g,v])=>(D.group_to_team[g]||g)+' lying '+v).join(' · ')+' (estimated from this board)':'Points lying unavailable: an in-house stone has no colour';
 table.innerHTML='<tr><th>Stone</th><th>Colour</th><th>Change</th><th>Moved (m)</th><th>After</th></tr>'+e.stones.filter(s=>s.change!=='unchanged'&&(s.in_play_before||s.in_play_after)).map(s=>
  '<tr><td>'+(s.after_tracker_id??s.before_tracker_id)+'</td><td>'+(s.colour||'unknown')+'</td><td>'+s.change.replaceAll('_',' ')+'</td><td>'+(s.displacement_m===null?'':s.displacement_m.toFixed(2))+'</td><td>'+(s.after_m?(s.in_play_after?'in play':'out of play'):'not observed')+'</td></tr>').join('');
 if(seek)video.currentTime=e.settle_interval_s[0];draw(video.currentTime)}
pick.onchange=()=>show();
document.querySelector('#play').onclick=()=>{const e=current();if(e.status==='unresolved'){video.currentTime=e.crossing_time_s;video.play();return}
 video.currentTime=Math.max(0,e.arrival_time_s-2);stopAt=e.settle_interval_s[1];video.play()};
document.querySelector('#after').onclick=()=>show();
function tick(t){if(stopAt!==null&&t>=stopAt){video.pause();stopAt=null}draw(t)}
if(video.requestVideoFrameCallback){const f=(_,m)=>{tick(m.mediaTime);video.requestVideoFrameCallback(f)};video.requestVideoFrameCallback(f)}
else video.addEventListener('timeupdate',()=>tick(video.currentTime));
video.addEventListener('loadedmetadata',()=>show());show(false);window.showThrow=show;
window.throwAudit=()=>({event:current().event_id,time:video.currentTime,status:document.querySelector('#status').textContent,points:document.querySelector('#points').textContent});
</script></html>'''


def run(*, public_run, states, config_path, match_config, output, video=None, track_colours=None,
        settings=None):
    public_run, output = Path(public_run), Path(output)
    if output.exists():
        raise ValueError('Preserve previous throw-effect output; choose a new directory')
    settings = {**DEFAULTS, **(settings or {})}
    config = json.loads(Path(config_path).read_text())
    hog = json.loads(Path(match_config).read_text())['local_hog_y_m']
    payload = json.loads(Path(states).read_text())
    protocol = json.loads((public_run/'protocol.json').read_text())
    if payload['source_sha256'] != protocol['source_sha256']:
        raise ValueError('Post-throw states do not match public run')
    colours = json.loads(Path(track_colours).read_text())['evidence'] if track_colours else None
    tracks = load_tracks(public_run/'match-observations.jsonl')
    records = payload['events']
    ends = [r['crossing_time_s'] for r in records[1:]]+[protocol['source_interval_s'][1]]
    events = [effect(r, tracks, house_radius_m=config['house_radius_m'],
                     stone_radius_m=config['stone_radius_m'], hog_y_by_panel=hog, settings=settings,
                     search_end_s=end, groups=list(config.get('group_to_team', {})) or None, colours=(colours or {}).get(r['proposal'].get('panel')))
              for r, end in zip(records, ends)]
    result = {'schema_version': 'curling-throw-effect-v1', 'development': True,
              'source_sha256': protocol['source_sha256'], 'events': events,
              'dimensions': {**{k: config[k] for k in ['house_radius_m', 'stone_radius_m']},
                             'sheet_half_width_m': settings['sheet_half_width_m'], 'hog_y_by_panel_m': hog},
              'group_to_team': config.get('group_to_team', {}),
              'summary': {'candidates': len(events),
                          'with_board_change': sum(e['status'] == 'review_proposal' for e in events),
                          'unresolved': [e['event_id'] for e in events if e['status'] == 'unresolved'],
                          'stone_colours': 'per_track_samples' if colours else 'unavailable',
                          'verified_settled_boards': 0, 'physical_identity_verified': False},
              'provenance': {'settings': settings, 'code_sha256': digest(__file__),
                             'input_sha256': {'observations': digest(public_run/'match-observations.jsonl'),
                                              'states': digest(states), 'config': digest(config_path),
                                              'match_config': digest(match_config),
                                              **({'track_colours': digest(track_colours)} if track_colours else {})},
                             'mode': 'Postprocessing replay; saved detection, tracking and geometry unchanged.'}}
    output.mkdir(parents=True)
    (output/'effects.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    (output/'effects.js').write_text('window.THROW_EFFECTS='+json.dumps(result, allow_nan=False)+';\n')
    video_url = html.escape(os.path.relpath(Path(video).resolve(), output.resolve()), quote=True) if video else ''
    (output/'index.html').write_text(VIEWER.replace('VIDEO_URL', video_url))
    return result


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('public-run', 'states', 'output'):
        parser.add_argument('--'+name, required=True)
    parser.add_argument('--config', dest='config_path', required=True)
    parser.add_argument('--match-config', required=True)
    parser.add_argument('--track-colours')
    parser.add_argument('--video')
    args = parser.parse_args()
    print(json.dumps(run(**vars(args))['summary']))
