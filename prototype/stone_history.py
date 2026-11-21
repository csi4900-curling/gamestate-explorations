"""Provisional histories from receiving-board observations in completed jobs."""
from collections import Counter
import json
import math


def histories(effects, frames, radius, step, fps):
    """Connect adjacent throw rows only across uninterrupted compatible observations."""
    events = effects['events']
    groups = {}
    membership = {}
    stops = {}
    checks = []
    next_events = {}
    for event in events:
        for i, stone in enumerate(event.get('stones', [])):
            if not (stone['in_play_before'] or stone['in_play_after']):
                continue
            key = f"{event['event_id']}/{i}"
            membership[key] = key
            groups[key] = [dict(key=key, event=event['event_id'], change=stone['change'],
                                after=stone['in_play_after'], time=event['crossing_time_s'],
                                colour_warning=stone['colour_differs_along_track'])]
    for first, second in zip(events, events[1:]):
        for i, stone in enumerate(first.get('stones', [])):
            if not stone['in_play_after']:
                continue
            key = f"{first['event_id']}/{i}"
            next_events[key] = second['event_id']
            if not second.get('settle_interval_s') or first['panel'] != second['panel']:
                stops[key] = 'Next receiving board unavailable or camera panel changed'
                continue
            point = stone['after_m']
            near = [(j,s) for j,s in enumerate(second['stones']) if s['in_play_before']
                    and math.dist(point, s['before_m']) <= radius]
            if len(near) != 1 or near[0][1]['before_tracker_id'] != stone['after_tracker_id']:
                stops[key] = 'No unique nearby continuation with the same track'
                continue
            j, target = near[0]
            if target['after_tracker_id'] != stone['after_tracker_id'] or target['after_m'] is None:
                stops[key] = 'Track lost or reassigned during the next throw'
                continue
            if (stone['colour_differs_along_track'] or target['colour_differs_along_track'] or
                    len({stone['colour'], target['colour']} - {None}) > 1):
                stops[key] = 'Conflicting colour evidence'
                continue
            start, end = first['settle_interval_s'][1], second['settle_interval_s'][1]
            if not start < second['arrival_time_s'] <= end:
                stops[key] = 'Overlapping or out-of-order receiving intervals'
                continue
            checks.append(dict(key=key, target=f"{second['event_id']}/{j}", point=point,
                               panel=first['panel'], track=stone['after_tracker_id'],
                               start=start, end=end, arrival=second['arrival_time_s'],
                               last_frame=None, last_point=None, known_end=None))
    # Check only active intervals in a single chronological pass through saved observations.
    claimed = Counter(c['target'] for c in checks)
    for c in checks:
        if claimed[c['target']] > 1:
            stops[c['key']] = 'Competing previous stones for one observation'
    ordered = iter(sorted(checks, key=lambda c:c['start']))
    pending = next(ordered, None)
    active = []
    # Track chronological collision-swap repairs recorded in effects.json so logical
    # stone IDs map cleanly back to raw tracker IDs in immutable match-observations.jsonl.
    swap_events = []
    for ev_idx, ev in enumerate(events):
        panel = ev.get('panel')
        for sw_idx, sw in enumerate(ev.get('collision_swaps_repaired') or []):
            tids = sw.get('tracker_ids') or []
            if panel and len(tids) == 2 and sw.get('swap_time_s') is not None:
                swap_events.append((float(sw['swap_time_s']), ev_idx, sw_idx, panel, tids[0], tids[1]))
    swap_events.sort()
    swap_pos = 0
    logical_to_raw = {}
    for row in frames:
        t = row['time_s']
        while swap_pos < len(swap_events) and swap_events[swap_pos][0] <= t + 1e-6:
            _, _, _, spanel, a, b = swap_events[swap_pos]
            l2r = logical_to_raw.setdefault(spanel, {})
            ra, rb = l2r.get(a, a), l2r.get(b, b)
            l2r[a], l2r[b] = rb, ra
            swap_pos += 1
        while pending and pending['start'] <= t + 1e-6:
            active.append(pending)
            pending = next(ordered, None)
        active = [c for c in active if c['end'] >= t - 1e-6 and c['key'] not in stops]
        if not active and pending is None:
            break
        for c in active:
            board = row['boards'][c['panel']]
            reg_status = (board.get('registration') or {}).get('status')
            if t < c['arrival'] and reg_status == 'geometry_skipped_inactive_interval':
                if c['last_frame'] is not None and row['frame_index'] - c['last_frame'] != step:
                    stops[c['key']] = f'Gap in sampled video at {t:.1f} s'
                c['last_frame'] = row['frame_index']
                continue
            stones = board['stones']
            raw_track = logical_to_raw.get(c['panel'], {}).get(c['track'], c['track'])
            own = [s.get('height_adjusted_local_m') for s in stones if s['tracker_id'] == raw_track]
            pos = own[0] if len(own) == 1 else None
            end = row.get('current_end')
            reason = None
            if (c['last_frame'] is None and t-c['start'] >= step/fps-1e-6 or
                    c['last_frame'] is not None and row['frame_index']-c['last_frame'] != step):
                reason = 'Gap in sampled video'
            elif end is not None and c['known_end'] is not None and end != c['known_end']:
                reason = 'Observed end changed'
            elif pos is None:
                reason = 'Stone missing or camera alignment unavailable'
            elif t < c['arrival'] and math.dist(pos, c['point']) > radius:
                reason = 'Stone moved between throws'
            elif c['last_point'] is not None and math.dist(pos, c['last_point']) > max(radius, 3.0 * step / fps if t >= c['arrival'] else radius):
                reason = 'Abrupt position change'
            elif any(s['tracker_id'] != raw_track and s.get('height_adjusted_local_m') is not None
                     and math.dist(pos, s['height_adjusted_local_m']) <= radius for s in stones):
                reason = 'Competing stone near the tracked position'
            if reason:
                stops[c['key']] = f'{reason} at {t:.1f} s'
            c.update(last_frame=row['frame_index'], last_point=pos)
            if end is not None:
                c['known_end'] = end
    for c in checks:
        key, target = c['key'], c['target']
        if key in stops:
            continue
        if c['last_frame'] is None or c['end'] - c['last_frame']/fps >= step/fps-1e-6:
            stops[key] = 'Observations ended before the next board settled'
            continue
        group = membership[key]
        groups[group].extend(groups.pop(target))
        membership[target] = group
    return dict(groups=groups, membership=membership, stops=stops, next_events=next_events, physical_identity_verified=False)


def from_job(job):
    def read(path):
        return json.loads((job/path).read_text())
    meta = read('observations/events.json')
    with (job/'observations/match-observations.jsonl').open() as stream:
        return histories(read('result/throws/effects.json'), map(json.loads, stream),
                         read('state.json')['stone_radius_m'], meta['sample_step_frames'], meta['source_fps'])
