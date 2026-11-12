"""Render one synchronized shared-rink view for a directional event aggregate.

The viewer plots both camera fragments in the same metric frame, marks the
unobserved middle as a gap (never interpolated), and optionally overlays board
stones mapped with the per-event observed camera roles. Identity remains
provisional and is displayed as such.
"""

import argparse
import json
import statistics
import os
from collections import OrderedDict
from pathlib import Path
from urllib.parse import quote

from prototype.rink_coordinates import rink_position


def role_timeline(events):
    rows = []
    for event in events:
        t = event["event_prediction"]["crossing_time_s"]
        for segment in event["segments"]:
            role = segment.get("role")
            panel = segment.get("rink_panel")
            if role in ("departure", "receiving") and panel in ("left", "right"):
                rows.append((t, panel, role))
    rows.sort()
    by_panel = {"left": [], "right": []}
    for t, panel, role in rows:
        history = by_panel[panel]
        if history and history[-1][1] == role:
            continue
        history.append((t, role))
    return by_panel


def role_at(timeline, panel, time_s):
    history = timeline.get(panel) or []
    if not history:
        return None
    chosen = None
    for t, role in history:
        if t <= time_s:
            chosen = role
        else:
            break
    return chosen


def compact_event(event):
    prediction = event["event_prediction"]
    segments = []
    starts = []
    ends = []
    unassigned = []
    # Explicit operator-requested display policy. This does not resolve the
    # aggregate's association status or create a cross-camera identity link.
    display_candidate = None
    if (not event.get('observation_only')
            and 'multiple_or_shared_counterpart_crossings' in event.get('association_issues', [])
            and any(s.get('role') == 'departure' and s['segment_id'].endswith(':primary')
                    for s in event['segments'])):
        candidates = [(s.get('hog_crossing_evidence', {}).get('crossing_time_s'), s['segment_id'])
                      for s in event['segments'] if s.get('role') == 'receiving']
        candidates = [(t, key) for t, key in candidates
                      if t is not None and t > prediction['crossing_time_s']]
        if candidates:
            first = min(t for t, key in candidates)
            earliest = [key for t, key in candidates if t == first]
            if len(earliest) == 1:
                display_candidate = earliest[0]
    for segment in event["segments"]:
        if (not event.get('observation_only')
                and 'multiple_or_shared_counterpart_crossings' in event.get('association_issues', [])
                and not segment.get('associated')
                and not segment['segment_id'].endswith(':primary')
                and segment['segment_id'] != display_candidate):
            unassigned.append(segment['segment_id'])
            continue
        original_samples = segment.get("geometry_samples", [])
        samples = [s for s in original_samples
                   if s.get("rink_position_m") is not None
                   and s.get('rink_position_kind') != 'ice_plane_unadjusted']
        pixels = segment.get("pixel_points") or []
        times = [s["time_s"] for s in samples]
        pixel_times = sorted({p['time_s'] for p in pixels})
        intervals = [b-a for a, b in zip(pixel_times, pixel_times[1:]) if b > a]
        step = segment.get('sample_step_s') or (statistics.median(intervals) if intervals else None)
        original_index = {s['time_s']: i for i, s in enumerate(original_samples)}
        breaks = [i == 0 or original_index[t] != original_index[times[i-1]] + 1
                  or (step is not None and t-times[i-1] > step*1.5 + 1e-6)
                  for i, t in enumerate(times)]
        segments.append({
            "id": segment["segment_id"],
            "role": segment.get("role"),
            "panel": segment.get("rink_panel"),
            "tracker_id": segment.get("tracker_id"),
            "status": segment.get("rink_coordinate_status"),
            "times": times,
            "break_before": breaks,
            "sample_step_s": step,
            "missing_geometry_times": [s['time_s'] for s in original_samples if s.get('rink_position_m') is None or s.get('rink_position_kind') == 'ice_plane_unadjusted'],
            "xy": [s["rink_position_m"] for s in samples],
            "kinds": [s.get("rink_position_kind") for s in samples],
            "pixel_times": [p["time_s"] for p in pixels],
            "pixels": [p["pixel"] for p in pixels],
        })
        if times:
            starts.append(times[0])
            ends.append(times[-1])
    links = []
    for link in event.get("cross_view_links", []):
        compact = {k: link.get(k) for k in (
            "departure_segment", "receiving_segment", "identity_status",
            "gap_m", "gap_s", "implied_speed_m_s", "gap_status",
            "speed_status", "spatial_consistency", "physical_identity_verified",
            "departure_colour", "receiving_colour", "colour_consistency",
        )}
        dt = link.get('gap_s')
        compact['temporal_relation'] = ('unknown' if dt is None else
                                         'overlap' if dt < 0 else
                                         'simultaneous_endpoints' if dt == 0 else 'unobserved_gap')
        compact['overlap_s'] = -dt if dt is not None and dt < 0 else None
        links.append(compact)
    return {
        "id": event["candidate_id"],
        "unassigned_segment_ids": unassigned,
        "display_receiving_candidate": display_candidate,
        "receiving_display_policy": "first_crossing_strictly_after_departure" if display_candidate else None,
        "observation_only":event.get('observation_only',False),
        "time_s": prediction["crossing_time_s"],
        "bracket_s": prediction.get("observed_bracket_s"),
        "start_s": min(starts) if starts else prediction["crossing_time_s"],
        "end_s": max(ends) if ends else prediction["crossing_time_s"],
        "segments": segments,
        "links": links,
        "association_issues": event.get("association_issues", []),
        "failure_reasons": event.get("failure_reasons", []),
        "direction": prediction.get("direction"),
        "line_id": prediction.get("line_id"),
        "physical_identity_verified": False,
        "colour": event.get("colour"),
        "colour_status": event.get("colour_status"),
        "camera_consistency": event.get("camera_consistency"),
        "throw_extent": event.get("throw_extent"),
    }


def write_board_chunks(observations_path, output_dir, events, hog_y_m,
                       board_hz=1.0, tee_distance=34.747):
    timeline = role_timeline(events)
    folder = output_dir / "board-data"
    folder.mkdir(exist_ok=True)
    chunks = OrderedDict()
    current = None
    rows = []
    last_kept = None
    sample_count = 0
    stone_count = 0

    def flush(key, rows):
        if key is None:
            return
        (folder / f"{key}.js").write_text(
            "window.receiveBoardChunk(" + str(key) + ","
            + json.dumps(rows, separators=(",", ":")).replace("<", "\\u003c") + ");\n")
        chunks[key] = [rows[0]["t"], rows[-1]["t"]]

    with Path(observations_path).open() as stream:
        for line in stream:
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            t = row["time_s"]
            if last_kept is not None and t - last_kept < 1.0 / board_hz - 1e-9:
                continue
            last_kept = t
            stones = []
            for panel in ("left", "right"):
                board = (row.get("boards") or {}).get(panel) or {}
                role = role_at(timeline, panel, t)
                if role not in ("departure", "receiving"):
                    continue
                for stone in board.get("stones", []):
                    local = stone.get("height_adjusted_local_m")
                    if local is None:
                        continue
                    try:
                        xy = rink_position(local, panel=panel, role=role,
                                           hog_y_m=hog_y_m,
                                           tee_distance=tee_distance)
                    except ValueError:
                        continue
                    stones.append([round(xy[0], 3), round(xy[1], 3),
                                   stone.get("tracker_id")])
                    stone_count += 1
            sample_count += 1
            key = int(t // 60)
            if current is None:
                current = key
            if key != current:
                flush(current, rows)
                rows = []
                current = key
            rows.append({"t": t, "s": stones})
    flush(current, rows)
    manifest = {
        "chunks": chunks,
        "sample_count": sample_count,
        "stone_count": stone_count,
        "board_hz": board_hz,
        "role_timeline": {panel: [[t, role] for t, role in history]
                          for panel, history in timeline.items()},
        "role_source": "per-event observed motion roles; carried forward until the next role change",
        "colour": None,
        "physical_identity_verified": False,
    }
    (folder / "manifest.js").write_text(
        "window.BOARD_MANIFEST=" + json.dumps(manifest, separators=(",", ":")) + ";\n")
    return manifest


def compact_state(state):
    teams = state.get("team_labels") or ["CAN", "SWE"]
    samples = []
    for row in state.get("samples", []):
        totals = row.get("last_observed_totals") or {}
        can = (totals.get(teams[0]) or {})
        swe = (totals.get(teams[1]) or {})
        samples.append([
            round(row["t"], 3),
            row.get("current_end"),
            "unknown" if row.get('current_end') is None else
            "observed" if str(row.get("current_end_status", "")).startswith("observed") else "inferred",
            row.get("deliveries_before"),
            (row.get("house") or {}).get("detected_stones_in_house"),
            can.get("value"), swe.get("value"),
            can.get("age_s"), swe.get("age_s"),
        ])
    return {"samples": samples, "team_labels": teams, "summary": state.get("summary"),
            "provenance_notes": (state.get("summary") or {}).get("notes")}


def render(aggregate_path, video, output_dir, *, match_observations=None,
           state_timeline=None, board_hz=1.0, title=None):
    aggregate_path = Path(aggregate_path)
    output_dir = Path(output_dir)
    aggregate = json.loads(aggregate_path.read_text())
    if aggregate.get("schema_version") != "directional-event-track-bridge-rink-v1":
        raise ValueError("Expected the enriched rink aggregate")
    if output_dir.exists():
        raise ValueError("Output exists; preserve the previous viewer")
    output_dir.mkdir(parents=True)
    events = [compact_event(event) for event in aggregate["events"]]
    hog_y_m = aggregate["rink_transform"]["hog_y_m"]
    board = None
    if match_observations is not None:
        board = write_board_chunks(match_observations, output_dir,
                                   aggregate["events"], hog_y_m, board_hz=board_hz)
    state = None
    if state_timeline is not None:
        state = compact_state(json.loads(Path(state_timeline).read_text()))
        (output_dir / "state-data.js").write_text(
            "window.STATE_DATA=" + json.dumps(state, separators=(",", ":")) + ";\n")
    payload = {
        "events": events,
        "track_pixel_coordinate_system": {
            "size_px": [640, 360],
            "origin": "full_frame_top_left",
            "source": "learned_event_aggregate.assemble normalizes pixel_points to 640x360",
        },
        "source_interval_s": aggregate.get("source_interval_s"),
        "scope":aggregate.get('scope'),
        "rink": aggregate["rink_coordinate_system"],
        "transform": aggregate["rink_transform"],
        "summary": aggregate.get("summary"),
        "board": {k: board[k] for k in ("chunks", "sample_count", "stone_count",
                                        "board_hz", "role_source", "colour",
                                        "physical_identity_verified")} if board else None,
        "provenance": aggregate.get("provenance"),
        "event_colour": aggregate.get("event_colour"),
        "handoff_colour": aggregate.get("handoff_colour"),
        "throw_extent_display": aggregate.get("throw_extent_display"),
    }
    (output_dir / "rink-data.js").write_text(
        "window.RINK_DATA=" + json.dumps(payload, separators=(",", ":")).replace("<", "\\u003c") + ";\n")
    url = quote(os.path.relpath(Path(video).resolve(), output_dir.resolve()))
    (output_dir / "index.html").write_text(
        TEMPLATE.replace("__DATA__", "rink-data.js").replace("__VIDEO__", url)
        .replace("__TITLE__", title or "Synchronized shared-rink trajectory review"))
    return {"events": len(events), "board": board, "state_samples":
            len(state["samples"]) if state else 0}


TEMPLATE = r'''<!doctype html><meta charset="utf-8"><title>__TITLE__</title>
<style>
body{font:16px system-ui;margin:22px;background:#f4f7f8;color:#21343d}
h1{font-size:23px;margin:0 0 8px}
.note{background:#fff5df;border-left:4px solid #c88700;padding:10px 12px;margin:10px 0;max-width:1200px}
main{display:grid;grid-template-columns:minmax(0,1fr) 440px;gap:18px}
video{display:block;width:100%;background:#000}
#source{position:relative}
#overlay{position:absolute;left:0;top:0;pointer-events:none;width:100%;height:100%}
#rink{background:#fff;border:1px solid #d7e0e3;width:440px;height:960px}
button,select{padding:8px;margin:4px 4px 4px 0}
#status{padding:9px 11px;background:#fff;min-height:52px;font-size:14px}
#meta{font-size:13px;max-width:1200px}
table{border-collapse:collapse;font-size:13px}td,th{padding:4px 8px;border-bottom:1px solid #dde5e8;text-align:left}
.legend span{display:inline-block;margin-right:12px}.sw{display:inline-block;width:12px;height:12px;border-radius:50%;margin-right:4px;vertical-align:-1px}
</style>
<h1>__TITLE__</h1>
<p class="note">Development output. Observed camera fragments are placed in a metric rink frame; unobserved gaps are retained. A standalone camera track does not establish an event or a camera link. Roles come from per-event observed motion. Physical stone identity is not verified. Height-adjusted positions are conditional estimates, not measured stone centres. Track markers show saved detector body-box centres. Metric accuracy is unmeasured.</p>
<select id="events"></select><button id="play">Play event interval</button><label class="small"><input id="showTracks" type="checkbox" checked> track markers</label><button id="back">-0.5 s</button><button id="next">+0.5 s</button>
<span class="legend"><span><i class="sw" style="background:#2166c9"></i>departure fragment</span><span><i class="sw" style="background:#d4791b"></i>receiving fragment</span><span><i class="sw" style="background:#7e8b91"></i>board stones (identity/colour unknown)</span><span class="small">track markers = body-box centres, not stone centres</span></span>
<main>
 <div>
  <div id="source"><video id="video" controls preload="metadata" src="__VIDEO__"></video><canvas id="overlay"></canvas></div>
  <div id="status"></div>
  
  <details><summary>Configuration and provenance</summary><pre id="meta"></pre></details>
 </div>
 <div><canvas id="rink" width="440" height="960"></canvas><p id="rink-note" style="font-size:13px"></p><table id="links"></table></div>
</main>
<script src="__DATA__"></script>
<script src="state-data.js" onerror="window.STATE_DATA=null"></script>
<script src="board-data/manifest.js" onerror="window.BOARD_MANIFEST=null"></script>
<script>
const D=window.RINK_DATA, B=window.BOARD_MANIFEST;
// Existing rink-data exports inherit the aggregate's documented 640x360 pixels.
const TRACK_IMAGE_SIZE=D.track_pixel_coordinate_system?.size_px||[640,360];
const video=document.getElementById('video'), overlay=document.getElementById('overlay');
const frameCallbacks=typeof video.requestVideoFrameCallback==='function';
let presentedTime=null;
if(frameCallbacks){
 const presented=(now,metadata)=>{presentedTime=metadata.mediaTime;video.requestVideoFrameCallback(presented)};
 video.requestVideoFrameCallback(presented);
}
const rink=document.getElementById('rink'), ctx=rink.getContext('2d');
const sel=document.getElementById('events'), status=document.getElementById('status');
const SCALE=24, CX=220, BOTTOM=900;
window.RINK_SCALE=SCALE;
const px=x=>CX+x*SCALE, py=y=>BOTTOM-y*SCALE;
const boardCache={}; let boardLoading=new Set();
window.boardCache=boardCache;
window.receiveBoardChunk=(k,rows)=>{boardCache[k]=rows;boardLoading.delete(k)};
function loadBoard(t){if(!B||!B.chunks)return;const k=Math.floor(t/60);if(k in B.chunks&&!boardCache[k]&&!boardLoading.has(k)){boardLoading.add(k);const s=document.createElement('script');s.src='board-data/'+k+'.js';document.body.append(s)}}
D.events.forEach((e,i)=>{const o=document.createElement('option');o.value=i;o.textContent=e.id+' · '+e.time_s.toFixed(2)+' s · '+(e.colour||'colour?')+' · '+(e.links.length? e.links[0].spatial_consistency:'no link');sel.append(o)});
if(!D.events.length){const o=document.createElement('option');o.textContent='No events';sel.append(o)}
document.getElementById('meta').textContent=JSON.stringify({rink:D.rink,transform:D.transform,summary:D.summary,provenance:D.provenance,board:D.board},null,2);
function indexAt(times,t){let lo=0,hi=times.length;while(lo<hi){const m=(lo+hi)>>1;if(times[m]<=t+1e-6)lo=m+1;else hi=m}return Math.max(0,Math.min(times.length-1,lo-1))}
function nearestAt(times,t){const i=indexAt(times,t);return i+1<times.length&&Math.abs(times[i+1]-t)<Math.abs(times[i]-t)?i+1:i}
function drawRink(event,t){
 ctx.clearRect(0,0,rink.width,rink.height);
 ctx.fillStyle='#fff';ctx.fillRect(0,0,rink.width,rink.height);
 // sheet and markings
 // the sheet is |x|<=2.375 from y=0 to y=tee distance
 const left=px(-2.375), right=px(2.375), top=py(D.rink.tee_distance_m), bottom=py(0);
 ctx.strokeStyle='#c7d3d7';ctx.strokeRect(left,top,right-left,bottom-top);
 ctx.beginPath();ctx.moveTo(px(0),top);ctx.lineTo(px(0),bottom);ctx.strokeStyle='#dbe4e6';ctx.stroke();
 for(const y of [6.401, D.rink.tee_distance_m-6.401]){ctx.beginPath();ctx.moveTo(left,py(y));ctx.lineTo(right,py(y));ctx.strokeStyle='#9fb3ba';ctx.setLineDash([6,5]);ctx.stroke();ctx.setLineDash([])}
 function house(y){for(const r of [1.829,1.219,0.610]){ctx.beginPath();ctx.arc(px(0),py(y),r*SCALE,0,Math.PI*2);ctx.strokeStyle=r===1.829?'#9fb3ba':'#c7d3d7';ctx.stroke()}ctx.fillStyle='#6f8188';ctx.beginPath();ctx.arc(px(0),py(y),3,0,Math.PI*2);ctx.fill()}
 house(0);house(D.rink.tee_distance_m);
 ctx.fillStyle='#40545c';ctx.font='12px system-ui';ctx.fillText('delivery tee',px(0)+8,bottom-6);ctx.fillText('receiving tee',px(0)+8,top+14);
 ctx.fillText('hog',left+4,py(6.401)-4);ctx.fillText('hog',left+4,py(D.rink.tee_distance_m-6.401)-4);
 ctx.save();ctx.translate(14,py(17));ctx.rotate(-Math.PI/2);ctx.fillStyle='#7e8b91';ctx.fillText('longitudinal metres (0 delivery → '+D.rink.tee_distance_m.toFixed(1)+' receiving)',0,0);ctx.restore();
 // board stones at displayed time
 if(B&&B.chunks){const k=Math.floor(t/60);loadBoard(t);const rows=boardCache[k]||[];let row=null;for(const r of rows){if(r.t<=t+1e-6)row=r;else break}if(row){ctx.fillStyle='rgba(126,139,145,.55)';for(const s of row.s){ctx.beginPath();ctx.arc(px(s[0]),py(s[1]),3,0,Math.PI*2);ctx.fill()}}}
 const colors={departure:'#2166c9',receiving:'#d4791b'};
 for(const seg of event.segments){if(!seg.times.length)continue;const col=colors[seg.role]||'#6f8188';ctx.strokeStyle=col;ctx.fillStyle=col;ctx.lineWidth=2;ctx.beginPath();seg.xy.forEach((p,i)=>{const X=px(p[0]),Y=py(p[1]);i&&!seg.break_before?.[i]?ctx.lineTo(X,Y):ctx.moveTo(X,Y)});ctx.stroke();for(const p of seg.xy){ctx.beginPath();ctx.arc(px(p[0]),py(p[1]),1.6,0,Math.PI*2);ctx.fill()}const st0=seg.times[0],st1=seg.times[seg.times.length-1];if(t>=st0-1e-6&&t<=st1+1e-6){const i=nearestAt(seg.times,t);if(Math.abs(t-seg.times[i])>(seg.sample_step_s??0)/2+1e-6)continue;const p=seg.xy[i];ctx.beginPath();ctx.arc(px(p[0]),py(p[1]),5,0,Math.PI*2);ctx.fillStyle='#fff';ctx.fill();ctx.strokeStyle=col;ctx.lineWidth=3;ctx.stroke()}}
 for(const link of event.links){if(link.temporal_relation!=='unobserved_gap')continue;const a=event.segments.find(s=>s.id===link.departure_segment),b=event.segments.find(s=>s.id===link.receiving_segment);if(!a||!b||!a.xy.length||!b.xy.length)continue;const A=a.xy[a.xy.length-1],Bp=b.xy[0];ctx.beginPath();ctx.moveTo(px(A[0]),py(A[1]));ctx.lineTo(px(Bp[0]),py(Bp[1]));ctx.strokeStyle=link.spatial_consistency==='consistent'?'#7e8b91':'#c0392b';ctx.setLineDash([5,5]);ctx.lineWidth=2;ctx.stroke();ctx.setLineDash([]);ctx.fillStyle='#5b6b72';ctx.font='12px system-ui';ctx.fillText('gap '+link.gap_m.toFixed(2)+' m / '+link.gap_s.toFixed(2)+' s',(px(A[0])+px(Bp[0]))/2+6,(py(A[1])+py(Bp[1]))/2)}
 document.getElementById('rink-note').textContent='Equal x/y scale: '+SCALE+' px per metre. Grey dots are detected board stones at the displayed source time; they are not verified stone identities and colour is unknown. Trajectory breaks retain missing geometry and observation gaps.';
}
function drawOverlay(event,t){
 window.overlayAudit=[];
 if(!video.videoWidth){overlay.width=0;overlay.height=0;return}
 overlay.width=video.videoWidth;overlay.height=video.videoHeight;const c=overlay.getContext('2d');c.clearRect(0,0,overlay.width,overlay.height);const show=document.getElementById('showTracks');if(!show||!show.checked)return;
 if(video.seeking||(frameCallbacks&&presentedTime===null))return;
 const sx=overlay.width/TRACK_IMAGE_SIZE[0],sy=overlay.height/TRACK_IMAGE_SIZE[1];
 for(const seg of event.segments){if(!seg.pixel_times.length)continue;const st0=seg.pixel_times[0],st1=seg.pixel_times[seg.pixel_times.length-1];if(t<st0-1e-6||t>st1+1e-6)continue;const i=nearestAt(seg.pixel_times,t);if(Math.abs(t-seg.pixel_times[i])>(seg.sample_step_s??0)/2+1e-6)continue;const saved=seg.pixels[i],p=[saved[0]*sx,saved[1]*sy];window.overlayAudit.push({segment_id:seg.id,tracker_id:seg.tracker_id,panel:seg.panel,video_time_s:t,sample_time_s:seg.pixel_times[i],saved_pixel:saved,source_pixel:p,scale:[sx,sy]});c.strokeStyle=seg.role==='departure'?'#2166c9':'#d4791b';c.lineWidth=2.5;c.beginPath();c.moveTo(p[0]-7,p[1]);c.lineTo(p[0]+7,p[1]);c.moveTo(p[0],p[1]-7);c.lineTo(p[0],p[1]+7);c.stroke();c.beginPath();c.arc(p[0],p[1],2.5,0,Math.PI*2);c.fillStyle=c.strokeStyle;c.fill();c.font='12px system-ui';c.fillStyle=c.strokeStyle;c.fillText(seg.role+' '+seg.tracker_id,p[0]+10,p[1]-8)}
}
function linkTiming(link){if(link.temporal_relation==='overlap')return 'overlap '+link.overlap_s.toFixed(2)+' s; compare simultaneous observations';if(link.temporal_relation==='simultaneous_endpoints')return 'fragment endpoints share a source timestamp';if(link.temporal_relation==='unknown')return 'fragment timing unavailable';return 'unobserved gap '+link.gap_m.toFixed(2)+' m / '+link.gap_s.toFixed(2)+' s; speed '+(link.implied_speed_m_s===null?'unknown':link.implied_speed_m_s.toFixed(2)+' m/s')+'; '+link.spatial_consistency}
function stateAt(t){if(!window.STATE_DATA||!window.STATE_DATA.samples.length||t<window.STATE_DATA.samples[0][0]-1e-6)return null;let lo=0,hi=window.STATE_DATA.samples.length;while(lo<hi){const m=(lo+hi)>>1;if(window.STATE_DATA.samples[m][0]<=t+1e-6)lo=m+1;else hi=m}return window.STATE_DATA.samples[Math.max(0,Math.min(window.STATE_DATA.samples.length-1,lo-1))]}
let stopAt=null;
function draw(){
 if(!D.events.length){drawRink({segments:[],links:[]},0);return}
 const event=D.events[Number(sel.value)];
 window.currentEvent=event;
 const t=presentedTime??(video.readyState>=1?video.currentTime:event.time_s);
 if(stopAt!==null&&!video.seeking&&t>=stopAt){video.pause();stopAt=null}
 window.frameAudit={presented_time_s:presentedTime,requested_time_s:video.currentTime,waiting_for_frame:video.seeking||(frameCallbacks&&presentedTime===null)};
 drawRink(event,t);drawOverlay(event,t);
 const link=event.links[0];status.textContent='Source '+t.toFixed(2)+' s · '+event.id+' crossing '+event.time_s.toFixed(2)+' s'+(event.observation_only?' · unresolved camera observation':'')+' · '+(link?('handoff '+link.identity_status+'; '+linkTiming(link)+(link.colour_consistency?('; colour '+link.colour_consistency):'')):'no cross-view link')+' · colour '+(event.colour||'unknown')+' ('+(event.colour_status||'unavailable')+'; not team/identity) · physical identity unverified';
 if(event.throw_extent){status.textContent+=event.throw_extent.status==='quiet_board_proposal'?' · throw ends '+event.throw_extent.end_time_s.toFixed(1)+' s':' · throw end unresolved ('+event.throw_extent.reason+')'}
 const agreement=event.camera_consistency;
 if(event.display_receiving_candidate)status.textContent+=' · receiving candidate shown: first crossing strictly after departure (display rule; association unresolved)';
 if(event.unassigned_segment_ids?.length)status.textContent+=' · '+event.unassigned_segment_ids.length+' ambiguous camera fragments excluded from this event; review them in unresolved camera tracks';
 if(agreement)status.textContent+=agreement.paired_samples?' · camera disagreement: median '+agreement.median_m.toFixed(2)+' m, max '+agreement.maximum_m.toFixed(2)+' m across '+agreement.paired_samples+' simultaneous samples (not absolute accuracy)':' · camera agreement unavailable: no comparable simultaneous observations';
 requestAnimationFrame(draw)
}
function choose(){stopAt=null;video.pause();const e=D.events[Number(sel.value)];if(!e)return;video.currentTime=Math.max(0,e.time_s);}
sel.onchange=choose;
document.getElementById('play').onclick=()=>{const e=D.events[Number(sel.value)];if(!e)return;video.currentTime=Math.max(0,e.start_s);stopAt=e.end_s;video.play()};
document.getElementById('back').onclick=()=>{stopAt=null;video.pause();video.currentTime=Math.max(0,video.currentTime-0.5)};
document.getElementById('next').onclick=()=>{stopAt=null;video.pause();video.currentTime=Math.min(video.duration||1e9,video.currentTime+0.5)};
video.addEventListener('pause',()=>{stopAt=null});
video.addEventListener('loadedmetadata',choose);if(video.readyState>=1)choose();
draw();
</script>'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--aggregate-rink", type=Path, required=True)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--match-observations", type=Path)
    parser.add_argument("--state-timeline", type=Path)
    parser.add_argument("--board-hz", type=float, default=1.0)
    parser.add_argument("--title")
    args = parser.parse_args()
    result = render(args.aggregate_rink, args.video, args.output_dir,
                    match_observations=args.match_observations,
                    state_timeline=args.state_timeline,
                    board_hz=args.board_hz, title=args.title)
    print(json.dumps({"events": result["events"],
                      "board": result["board"]["sample_count"] if result["board"] else None,
                      "state_samples": result["state_samples"]}))


if __name__ == "__main__":
    main()
