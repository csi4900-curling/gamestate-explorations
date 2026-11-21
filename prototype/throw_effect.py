"""Per-throw board change from saved public-pipeline observations.

Replays existing tracker observations and post-throw proposals; it does not
rerun detection, tracking or geometry. For each event candidate it compares the
receiving-panel stones before the delivered stone arrives with those in the
first interval where no in-play stone moves, and keeps the observed paths of
the delivered stone and of stones that moved.
Positions inherit unverified calibration. A tracker ID is not physical identity;
only stationary stones are re-linked, by the physical exclusion of two stone
centres within one radius. Collision identity through an ID change stays open.
"""
from bisect import bisect_left, bisect_right
import html
import json
import math
import os
from pathlib import Path
from statistics import median

from prototype.detection_cache import digest
from prototype.house_points import points_lying
from prototype.scripts.enrich_rink_aggregate import rink_endpoints

DEFAULTS = {
    'before_window_s': 2.0,
    'before_guard_s': 0.1,
    'minimum_window_samples': 3,
    'moved_minimum_m': 0.05,
    'moved_scatter_factor': 3.0,
    'sheet_half_width_m': 2.375,
    'quiet_window_s': 2.0,
    'quiet_search_step_s': 0.5,
    'quiet_tail_s': 3.0,
    'provenance': 'Engineering defaults for a development replay; not validated thresholds.',
}


def load_tracks_and_registration(path):
    """Receiving observations by panel/tracker and registered frame timestamps per panel."""
    tracks = {}
    registered = {'left': [], 'right': []}
    with Path(path).open() as stream:
        for line in stream:
            row = json.loads(line)
            t = row['time_s']
            for panel, board in row['boards'].items():
                if board.get('homography_normalized_pixels_to_local_metres') is not None:
                    registered.setdefault(panel, []).append(t)
                for stone in board['stones']:
                    if stone.get('tracker_id') is None:
                        continue
                    tracks.setdefault(panel, {}).setdefault(stone['tracker_id'], []).append(
                        (t, stone.get('height_adjusted_local_m')))
    return tracks, registered


def load_tracks(path):
    """Receiving observations by panel and tracker: [(time_s, position or None)]."""
    tracks, _ = load_tracks_and_registration(path)
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


def quiet_interval(panel_tracks, delivered, start, end, region, settings, *, registered_times=None):
    """Earliest window in which no in-play stone shows net displacement.

    The saved motion posterior alternates on pixel jitter for resting stones, and
    the longest low-motion run can fall during later handling. Here each track's
    half-window medians are compared; later clearing cannot move the choice
    earlier. An unobserved delivered stone that reappears in play later blocks
    the window instead of being assumed at rest. An empty house after the
    delivered stone exits is still accepted when camera registration supports
    both halves of the window.
    """
    span, minimum = settings['quiet_window_s'], settings['minimum_window_samples']
    last_delivered = max((t for t, p in panel_tracks[delivered] if p is not None and region(p)), default=None)
    t = start
    while t+span <= end:
        quiet = True
        supported = False
        for tracker_id, samples in panel_tracks.items():
            a = window(samples, t, t+span/2, minimum)
            b = window(samples, t+span/2, t+span, minimum)
            if a is None or b is None:
                if tracker_id == delivered and last_delivered is not None and last_delivered > t:
                    quiet = False; break
                present = a or b
                if present is not None and (tracker_id == delivered or region(present['position_m'])):
                    h0, h1 = (t, t+span/2) if a is not None else (t+span/2, t+span)
                    pts = [p for ts, p in samples if h0 <= ts <= h1 and p is not None]
                    mid = len(pts)//2
                    if mid >= 1 and math.dist(
                        [median(p[0] for p in pts[:mid]), median(p[1] for p in pts[:mid])],
                        [median(p[0] for p in pts[mid:]), median(p[1] for p in pts[mid:])],
                    ) > settings['moved_minimum_m']:
                        quiet = False; break
                continue
            # The delivered stone counts wherever it is: it arrives from outside the region.
            supported |= tracker_id == delivered or region(a['position_m']) or region(b['position_m'])
            if ((tracker_id == delivered or region(a['position_m']) or region(b['position_m'])) and
                    math.dist(a['position_m'], b['position_m']) > settings['moved_minimum_m']):
                quiet = False; break
        if quiet and not supported and registered_times is not None and (last_delivered is None or t > last_delivered):
            mid_t = t + span / 2
            n_first = bisect_right(registered_times, mid_t) - bisect_left(registered_times, t)
            n_second = bisect_right(registered_times, t + span) - bisect_left(registered_times, mid_t)
            if n_first >= minimum and n_second >= minimum:
                supported = True
        if quiet and supported:
            return [t, t+span]
        t += settings['quiet_search_step_s']
    return None


def throw_extents(aggregate, observations, *, house_radius_m, stone_radius_m, hog_y_by_panel, settings=None):
    """End each event's receiving trajectory at its first quiet board.

    A receiving track otherwise continues until the tracker loses the stone or the
    next candidate arrives, so later sweeping, clearing or repositioning is drawn as
    part of the throw. Returns the aggregate annotated with every event's extent
    (all samples retained) and a display copy whose receiving segments stop at that
    extent. Events without one receiving segment or without a quiet interval are
    left whole and marked unresolved; nothing is trimmed by hand.
    """
    settings = {**DEFAULTS, **(settings or {})}
    tracks, registered = load_tracks_and_registration(observations)
    crossings = sorted(e['event_prediction']['crossing_time_s'] for e in aggregate['events'])

    def extent_of(receiver, search_end):
        panel = receiver.get('rink_panel') or {'left_split': 'left', 'right_split': 'right'}[receiver['camera']]
        samples = tracks.get(panel, {}).get(receiver.get('tracker_id'))
        if not samples:
            return {'status': 'unresolved', 'reason': 'receiving_track_missing_from_observations'}

        def region(position):
            return in_play(position, hog_y_by_panel[panel], half_width_m=settings['sheet_half_width_m'],
                           house_radius_m=house_radius_m, stone_radius_m=stone_radius_m)

        quiet = quiet_interval(tracks[panel], receiver['tracker_id'], samples[0][0], search_end, region, settings,
                               registered_times=registered.get(panel))
        if quiet is None:
            return {'status': 'unresolved', 'reason': 'no_quiet_board_interval_before_next_candidate'}
        end_time_s = round(min(quiet[1]+settings['quiet_tail_s'], search_end), 3)
        return {'status': 'quiet_board_proposal', 'end_time_s': end_time_s, 'quiet_interval_s': quiet,
                'tail_s': round(end_time_s-quiet[1], 3),
                'basis': 'Earliest window with no net in-play stone displacement after arrival, plus a trailing tail bounded by the next candidate.',
                # False when the tracker lost the stone first: the board is quiet, the stone's rest is unseen.
                'stone_observed_in_quiet_interval': any(quiet[0] <= t <= quiet[1] and pos is not None
                                                       for t, pos in samples),
                'verified_settled_board': False}

    annotated = []; display = []
    for event in aggregate['events']:
        crossing = event['event_prediction']['crossing_time_s']
        search_end = next((t for t in crossings if t > crossing), aggregate['source_interval_s'][1])
        extents = {s['segment_id']: extent_of(s, search_end) for s in event['segments']
                   if s.get('role') == 'receiving' and s.get('pixel_points')}
        # Competing receiving hypotheses are each limited by their own stone; none is chosen here.
        summary = (next(iter(extents.values())) if len(extents) == 1 else
                   {'status': 'unresolved', 'reason': 'missing_or_ambiguous_receiving_segment',
                    'receiving_segments': extents})
        annotated.append({**event, 'throw_extent': summary})
        segments = []
        for segment in event['segments']:
            extent = extents.get(segment['segment_id'])
            if not extent or extent['status'] != 'quiet_board_proposal':
                segments.append(segment); continue
            kept = {key: [p for p in segment.get(key, []) if p['time_s'] <= extent['end_time_s']]
                    for key in ('pixel_points', 'geometry_samples')}
            segments.append({**segment, **kept, **rink_endpoints(kept['geometry_samples']), 'samples_after_throw_end_not_displayed':
                             len(segment.get('pixel_points', []))-len(kept['pixel_points'])})
        display.append({**annotated[-1], 'segments': segments})
    scope = 'Receiving trajectories are displayed up to each event\'s proposed throw end; the full aggregate retains every sample.'
    return {**aggregate, 'events': annotated}, {**aggregate, 'events': display, 'throw_extent_display': scope}


def _clone_colours(colours):
    if not colours:
        return None
    return {
        k: {**v, 'samples': [dict(s) for s in v.get('samples', [])]}
        for k, v in colours.items()
    }


def repair_collision_swaps(panel_tracks, colours, delivered, window_start, window_end,
                           stone_radius_m, region, *, delivered_colour_hint=None):
    """Repair tracker ID swaps at hard-sphere stone collisions within one throw window.

    At lower frame rates (e.g. 5 Hz) a constant-velocity tracker can swap IDs
    when an incoming stone transfers momentum to a resting stone: the struck
    stone shoots along the incoming velocity vector while the incoming stone
    stops or deflects near the impact point. Because physical stones cannot
    pass through each other, the true assignment has a strictly smaller step
    sum than the swapped assignment, and opposite-colour collisions also invert
    track colours across the impact timestamp.

    Operates on the provided mutable dicts (callers should pass throw-local or
    panel-local copies) and returns a list of explicit repair provenance records.
    """
    applied = []
    seen = set()
    max_swaps = 16

    def colour_before(tid, t_cutoff):
        if colours:
            samps = [r for r in colours.get(str(tid), {}).get('samples', [])
                     if r.get('prediction') and r['time_s'] <= t_cutoff + 0.05]
            if samps:
                return max(samps, key=lambda r: r['time_s'])['prediction']
        if tid == delivered and delivered_colour_hint:
            return delivered_colour_hint
        return None

    def colour_after(tid, t_cutoff):
        if not colours:
            return None
        samps = sorted(
            [r for r in colours.get(str(tid), {}).get('samples', [])
             if r.get('prediction') and r['time_s'] >= t_cutoff - 0.05],
            key=lambda r: r['time_s'],
        )
        if not samps:
            return None
        # Immediate post-impact sample within this throw window is always relevant.
        if samps[0]['time_s'] <= window_end + 2.0:
            return samps[0]['prediction']
        # A later sample (e.g. from sparse track-wide sampling) is only trusted
        # if the track remained in play at the end of this throw; stones that
        # exited behind the backboards can overlap parked stones much later.
        post_pts = [p for t, p in panel_tracks.get(tid, [])
                    if t_cutoff <= t <= window_end + 0.5 and p is not None]
        if post_pts and region(post_pts[-1]):
            return samps[0]['prediction']
        return None

    for _ in range(max_swaps):
        active = {}
        for tid, samples in panel_tracks.items():
            sub = {t: p for t, p in samples if window_start <= t <= window_end and p is not None}
            if len(sub) >= 2:
                active[tid] = sub
        tids = sorted(active)
        best = None
        for i, a in enumerate(tids):
            da = active[a]
            for b in tids[i+1:]:
                db = active[b]
                common = sorted(set(da) & set(db))
                if len(common) < 2:
                    continue
                for k in range(len(common) - 1):
                    t_prev, t_cur = common[k], common[k+1]
                    if t_cur - t_prev <= 0 or t_cur - t_prev > 0.65:
                        continue
                    if (a, b, t_cur) in seen:
                        continue
                    ap, ac = da[t_prev], da[t_cur]
                    bp, bc = db[t_prev], db[t_cur]
                    if min(math.dist(ap, bp), math.dist(ac, bc)) > 5.0 * stone_radius_m:
                        continue
                    d_unswapped = math.dist(ap, ac) + math.dist(bp, bc)
                    d_swapped = math.dist(ap, bc) + math.dist(bp, ac)
                    saving = d_unswapped - d_swapped
                    if d_unswapped <= 0 or d_swapped >= 0.75 * d_unswapped or saving < 0.15:
                        continue
                    ba, bb = colour_before(a, t_prev), colour_before(b, t_prev)
                    aa, ab = colour_after(a, t_cur), colour_after(b, t_cur)
                    opposite_before = ba is not None and bb is not None and ba != bb
                    a_flipped = opposite_before and aa == bb
                    b_flipped = opposite_before and ab == ba
                    a_kept = opposite_before and aa == ba
                    b_kept = opposite_before and ab == bb
                    basis = None
                    if opposite_before and (a_flipped or b_flipped) and not (a_kept or b_kept):
                        basis = 'opposite_colour_and_kinematic_collision_swap'
                    elif (not (a_kept or b_kept)
                          and d_swapped < 0.50 * d_unswapped
                          and saving >= 0.30
                          and max(math.dist(ap, ac), math.dist(bp, bc)) >= 2.0 * stone_radius_m):
                        basis = 'kinematic_collision_swap_unverified'
                    if basis is None:
                        continue
                    cand = (t_cur, -saving, a, b, t_prev, t_cur, d_unswapped, d_swapped, basis, ba, aa, bb, ab)
                    if best is None or cand[:2] < best[:2]:
                        best = cand
        if best is None:
            break
        _, _, a, b, t_prev, t_cur, d_unswapped, d_swapped, basis, ba, aa, bb, ab = best
        seen.add((a, b, t_cur))
        # Swap trajectory tails from t_cur onwards.
        sa, sb = panel_tracks[a], panel_tracks[b]
        panel_tracks[a] = [x for x in sa if x[0] < t_cur] + [x for x in sb if x[0] >= t_cur]
        panel_tracks[b] = [x for x in sb if x[0] < t_cur] + [x for x in sa if x[0] >= t_cur]
        # Swap post-impact colour samples from t_cur onwards so colour consistency follows physical stones.
        if colours is not None:
            ka, kb = str(a), str(b)
            ea = colours.setdefault(ka, {'samples': []})
            eb = colours.setdefault(kb, {'samples': []})
            ca, cb = ea.get('samples', []), eb.get('samples', [])
            ea['samples'] = [r for r in ca if r['time_s'] < t_cur] + [r for r in cb if r['time_s'] >= t_cur]
            eb['samples'] = [r for r in cb if r['time_s'] < t_cur] + [r for r in ca if r['time_s'] >= t_cur]
        applied.append({
            'tracker_ids': [a, b],
            'prev_time_s': t_prev,
            'swap_time_s': t_cur,
            'unswapped_step_sum_m': round(d_unswapped, 4),
            'swapped_step_sum_m': round(d_swapped, 4),
            'basis': basis,
            'colour_before': {str(a): ba, str(b): bb},
            'colour_after_raw': {str(a): aa, str(b): ab},
            'physical_identity_verified': False,
        })
    return applied


def effect(record, tracks, *, house_radius_m, stone_radius_m, hog_y_by_panel, settings, search_end_s,
           colours=None, groups=None, registered_times=None, delivered_colour_hint=None,
           mutate_state=False):
    proposal = record['proposal']
    base = {'event_id': record['event_id'], 'crossing_time_s': record['crossing_time_s']}
    if 'time_s' not in proposal:
        return {**base, 'status': 'unresolved', 'reason': proposal.get('reason')}
    panel, delivered = proposal['panel'], proposal['receiving_tracker_id']
    raw_panel_tracks = tracks.get(panel, {})
    if delivered not in raw_panel_tracks:
        return {**base, 'status': 'unresolved', 'reason': 'delivered_track_missing_from_observations'}
    panel_tracks = raw_panel_tracks if mutate_state else {k: list(v) for k, v in raw_panel_tracks.items()}
    working_colours = colours if mutate_state else _clone_colours(colours)
    arrival = panel_tracks[delivered][0][0]

    def region(position):
        return in_play(position, hog_y_by_panel[panel], half_width_m=settings['sheet_half_width_m'],
                       house_radius_m=house_radius_m, stone_radius_m=stone_radius_m)

    settle = quiet_interval(panel_tracks, delivered, arrival, search_end_s, region, settings,
                            registered_times=registered_times)
    if settle is None:
        return {**base, 'status': 'unresolved', 'reason': 'no_quiet_board_interval_before_next_candidate',
                'panel': panel, 'delivered_tracker_id': delivered, 'arrival_time_s': arrival}
    swaps_repaired = repair_collision_swaps(
        panel_tracks, working_colours, delivered, arrival - 0.5, settle[1],
        stone_radius_m, region, delivered_colour_hint=delivered_colour_hint,
    )
    if swaps_repaired:
        settle = quiet_interval(panel_tracks, delivered, arrival, search_end_s, region, settings,
                                registered_times=registered_times) or settle
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
            colour, switched = colour_at(working_colours, old, arrival, not_after=True)
            later = colour_at(working_colours, new, middle)[0] if a else None
        else:
            colour, switched = colour_at(working_colours, new, middle)
            if new == delivered and colour is None and delivered_colour_hint:
                colour = delivered_colour_hint
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
    delivered_row = next((s for s in stones if s['after_tracker_id'] == delivered), None)
    delivered_colour = (delivered_row['colour'] if delivered_row and delivered_row['colour']
                        else colour_at(working_colours, delivered, arrival)[0] or delivered_colour_hint)
    # The delivered stone's path is kept even when it leaves play and has no board row.
    moving = {delivered} | {s['before_tracker_id'] if s['before_tracker_id'] is not None else s['after_tracker_id']
                            for s in stones if s['change'] != 'unchanged'}
    board = [{'observation_id': s['after_tracker_id'], 'position_m': s['after_m'], 'group': s['colour']}
             for s in stones if s['in_play_after']]
    points = points_lying(board, house_radius_m=house_radius_m, stone_radius_m=stone_radius_m,
                          groups=groups) if groups else None
    for s in stones:
        if s['change'] == 'moved' and s['after_tracker_id'] != s['before_tracker_id']:
            moving.add(s['after_tracker_id'])
    return {**base, 'status': 'review_proposal', 'panel': panel, 'delivered_tracker_id': delivered,
            'delivered_colour': delivered_colour,
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
            'superseded_motion_proposal_interval_s': proposal.get('stationary_interval_s'),
            'collision_swaps_repaired': swaps_repaired,
            'tracks_with_inconsistent_colour': [s['after_tracker_id'] if s['after_tracker_id'] is not None
                                           else s['before_tracker_id'] for s in stones
                                           if s['colour_differs_along_track']
                                           and (s['in_play_before'] or s['in_play_after'] or s['change'] == 'delivered')],
            'limitations': ['Quiet-window proposal is not a verified settled board.',
                            'A stone whose tracker ID changes while moving appears as lost plus appeared.',
                            'A moving stone without observations in a window cannot block that window.',
                            'Positions inherit unverified calibration; displacement is not a validated measurement.']}


VIEWER = '''<!doctype html><html lang="en"><meta charset="utf-8">
<title>Throws</title>
<style>body{font:16px system-ui;margin:24px;color:#233746}select,button{font:inherit;padding:8px}
video{width:100%;display:block}main{max-width:1440px}.views{display:grid;grid-template-columns:2fr 1fr;gap:16px}
canvas{width:100%;background:#f4f8fa}.note{background:#fff5d9;padding:12px}table{border-collapse:collapse;font-size:14px}
td,th{padding:3px 8px;text-align:left;border-bottom:1px solid #d5e1e4}#points{font-size:20px;font-weight:600}
#context{font-size:14px;color:#3d5c66;margin:6px 0}#spinBox{margin-top:12px;padding:10px 12px;background:#f4f8fa;border:1px solid #d5e1e4;border-radius:6px;font-size:14px}
#spinStrip{display:block;max-width:100%;margin-top:8px;border-radius:4px;image-rendering:auto}</style><main>
<h1>Throws</h1>
<p class="note">Each throw: receiving-house stones before the delivered stone arrives, observed paths of stones that moved, and the board in the first quiet interval afterwards. Positions depend on calibration; tracker IDs are provisional and the quiet interval is a proposal.</p>
<select id="pick" aria-label="Throw"></select> <button id="play">Play throw</button> <button id="after">Go to board after</button>
<div class="views"><div><video id="video" controls preload="metadata" src="VIDEO_URL"></video>
<p id="context"></p><p id="status"></p><p id="points"></p><table id="changes"></table>
<div id="spinBox" hidden><div id="spinObs"></div><div id="spinModel" style="color:#5c6f77;margin-top:4px"></div><img id="spinStrip" alt="Stabilized stone crop strip" hidden></div></div>
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
 if(e.delivered_colour&&!colourOf[e.delivered_tracker_id])colourOf[e.delivered_tracker_id]=e.delivered_colour;
 for(const [id,rows] of Object.entries(e.paths)){ctx.strokeStyle=fill[colourOf[id]]||'#777';ctx.lineWidth=2;let last=null;ctx.beginPath();
  for(const [time,x,y] of rows){if(x===null){last=null;continue}const p=f.px([x,y]);
   if(last!==null&&time-last<0.25)ctx.lineTo(...p);else ctx.moveTo(...p);last=time}ctx.stroke()}
 for(const s of e.stones){if(s.change!=='unchanged'&&s.before_m)stone(f,s.before_m,s.colour,{hollow:true,dash:[4,3]});
  if(s.after_m)stone(f,s.after_m,s.colour,{alpha:s.in_play_after?1:0.3})}
 if(t!==null&&t>=e.arrival_time_s-2.1&&t<=e.settle_interval_s[1])for(const [id,rows] of Object.entries(e.paths)){
  let best=null;for(const r of rows)if(r[1]!==null&&Math.abs(r[0]-t)<0.15&&(!best||Math.abs(r[0]-t)<Math.abs(best[0]-t)))best=r;
  if(best){const [x,y]=f.px([best[1],best[2]]);ctx.beginPath();ctx.arc(x,y,dim.stone_radius_m*S+4,0,Math.PI*2);ctx.lineWidth=3;ctx.strokeStyle='#0a84a8';ctx.stroke()}}}
function showSpin(e){const box=document.querySelector('#spinBox'),obs=document.querySelector('#spinObs'),mod=document.querySelector('#spinModel'),img=document.querySelector('#spinStrip');
 const r=e.revolutions;if(!r){box.hidden=true;return}box.hidden=false;const s=r.sending||{};
 if(s.period_s){const sense=s.sense?.screen_loop_sense?' · screen loop: '+s.sense.screen_loop_sense+' (unverified)':'';
  obs.textContent='Observed sending-view spin (development): '+s.period_s.toFixed(2)+' s/turn ('+s.rate_hz.toFixed(2)+' rev/s) · '+s.observed_turns_in_interval+' turns over '+s.duration_s.toFixed(1)+' s ['+s.basis+']'+sense;
 }else obs.textContent='Observed sending-view spin: unavailable ('+(s.basis||s.reason||s.status||'no clear peak')+').';
 const m=r.modeled_whole_throw_estimate;
 mod.textContent=m?'Modeled whole-throw extrapolation (not observed): ~'+m.estimated_turns+' turns over '+m.travel_duration_s.toFixed(1)+' s travel (constant-rate assumption).':'Whole-throw extrapolation unavailable.';
 if(s.filmstrip){img.src='spin/'+encodeURIComponent(s.filmstrip);img.hidden=false}else{img.removeAttribute('src');img.hidden=true}}
function show(seek=true){const e=current(),status=document.querySelector('#status'),points=document.querySelector('#points'),table=document.querySelector('#changes'),ctxEl=document.querySelector('#context');
 table.innerHTML='';points.textContent='';stopAt=null;
 const mc=e.match_context;ctxEl.textContent=mc?('Inferred End '+mc.end_index+' · Throw #'+mc.throw_in_end+(mc.team?' · '+mc.team:'')+(mc.rock_pair?' · Rule-based Rock Pair '+mc.rock_pair:'')+(mc.kinematics?' · Rec speed '+mc.kinematics.receiving_mean_speed_m_s+' m/s'+(mc.kinematics.lateral_curl_m!==null?' · Curl '+mc.kinematics.lateral_curl_m.toFixed(2)+' m':''):'')):'';
 showSpin(e);
 if(e.status==='unresolved'){status.textContent='No board change available: '+e.reason+'.';if(seek)video.currentTime=e.crossing_time_s;draw(null);return}
 status.textContent='Arrives '+e.arrival_time_s.toFixed(1)+' s · board after '+e.settle_interval_s[0].toFixed(1)+'–'+e.settle_interval_s[1].toFixed(1)+' s · in play '+e.in_play.before+' → '+e.in_play.after+
  (e.collision_swaps_repaired?.length?' · repaired '+e.collision_swaps_repaired.length+' collision ID swap'+(e.collision_swaps_repaired.length>1?'s':'')+' ('+e.collision_swaps_repaired.map(s=>s.tracker_ids.join('↔')+' @ '+s.swap_time_s.toFixed(1)+'s').join(', ')+')':'')+
  (e.tracks_with_inconsistent_colour.length?' · colour not consistent along track '+e.tracks_with_inconsistent_colour.join(', ')+' (identity may switch at some point)':'');
 const p=e.points_lying_after;if(p)points.textContent=p.conditional_points_by_group?Object.entries(p.conditional_points_by_group).map(([g,v])=>(D.group_to_team[g]||g)+' lying '+v).join(' · ')+' (estimated from this board)':'Points lying unavailable: an in-house stone has no colour';
 table.innerHTML='<tr><th>Stone</th><th>Colour</th><th>Change</th><th>Moved (m)</th><th>After</th></tr>'+e.stones.filter(s=>s.change!=='unchanged'&&(s.in_play_before||s.in_play_after)).map(s=>
  '<tr><td>'+(s.after_tracker_id??s.before_tracker_id)+'</td><td>'+(s.colour||'unknown')+'</td><td>'+s.change.replaceAll('_',' ')+'</td><td>'+(s.displacement_m===null?'':s.displacement_m.toFixed(2))+'</td><td>'+(s.after_m?(s.in_play_after?'in play':'out of play'):'not observed')+'</td></tr>').join('');
 if(seek)video.currentTime=e.settle_interval_s[0];draw(video.currentTime)}
pick.onchange=()=>show();
document.querySelector('#play').onclick=()=>{const e=current();if(e.status==='unresolved'){video.currentTime=e.crossing_time_s;video.play();return}
 video.currentTime=Math.max(0,e.arrival_time_s-2);stopAt=e.settle_interval_s[1];video.play()};
document.querySelector('#after').onclick=()=>show();
video.addEventListener('pause',()=>{stopAt=null});
function tick(t){if(stopAt!==null&&t>=stopAt){video.pause();stopAt=null}draw(t)}
if(video.requestVideoFrameCallback){const f=(_,m)=>{tick(m.mediaTime);video.requestVideoFrameCallback(f)};video.requestVideoFrameCallback(f)}
else video.addEventListener('timeupdate',()=>tick(video.currentTime));
video.addEventListener('loadedmetadata',()=>show());show(false);window.showThrow=show;
window.throwAudit=()=>({event:current().event_id,time:video.currentTime,status:document.querySelector('#status').textContent,points:document.querySelector('#points').textContent});
</script></html>'''


def _fallback_record(record, event_by_id):
    proposal = record['proposal']
    if 'time_s' in proposal or proposal.get('reason') not in (
            'no_observed_moving_to_stationary_transition', 'no_receiving_motion_observations'):
        return record
    event = event_by_id.get(record['event_id'])
    if not event:
        return record
    receivers = [s for s in event.get('segments', []) if s.get('role') == 'receiving' and s.get('pixel_points')]
    if len(receivers) != 1:
        return record
    receiver = receivers[0]
    panel = receiver.get('rink_panel') or {'left_split': 'left', 'right_split': 'right'}[receiver['camera']]
    return {**record, 'proposal': {'time_s': receiver['pixel_points'][0]['time_s'], 'panel': panel,
                                    'receiving_tracker_id': receiver['tracker_id'],
                                    'stationary_interval_s': None,
                                    'fallback': 'aggregate_receiving_segment'}}


def run(*, public_run, states, config_path, match_config, output, video=None, track_colours=None,
        aggregate=None, settings=None):
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
    event_by_id = ({e['candidate_id']: e for e in json.loads(Path(aggregate).read_text())['events']}
                   if aggregate else {})
    tracks, registered = load_tracks_and_registration(public_run/'match-observations.jsonl')
    repaired_tracks = {panel: {tid: list(s) for tid, s in ptracks.items()} for panel, ptracks in tracks.items()}
    repaired_colours = ({panel: _clone_colours(c) for panel, c in colours.items()}
                        if colours else None)
    records = [_fallback_record(r, event_by_id) for r in payload['events']]
    ends = [r['crossing_time_s'] for r in records[1:]]+[protocol['source_interval_s'][1]]
    events = []
    for r, end in zip(records, ends):
        panel = r['proposal'].get('panel')
        agg_ev = event_by_id.get(r['event_id']) or {}
        hint = agg_ev.get('colour') if isinstance(agg_ev.get('colour'), str) else None
        events.append(effect(
            r, repaired_tracks, house_radius_m=config['house_radius_m'],
            stone_radius_m=config['stone_radius_m'], hog_y_by_panel=hog, settings=settings,
            search_end_s=end, groups=list(config.get('group_to_team', {})) or None,
            colours=(repaired_colours or {}).get(panel),
            registered_times=registered.get(panel),
            delivered_colour_hint=hint,
            mutate_state=True,
        ))
    result = {'schema_version': 'curling-throw-effect-v1', 'development': True,
              'source_sha256': protocol['source_sha256'], 'events': events,
              'dimensions': {**{k: config[k] for k in ['house_radius_m', 'stone_radius_m']},
                             'sheet_half_width_m': settings['sheet_half_width_m'], 'hog_y_by_panel_m': hog},
              'group_to_team': config.get('group_to_team', {}),
              'summary': {'candidates': len(events),
                          'with_board_change': sum(e['status'] == 'review_proposal' for e in events),
                          'unresolved': [e['event_id'] for e in events if e['status'] == 'unresolved'],
                          'collision_swaps_repaired': sum(len(e.get('collision_swaps_repaired', [])) for e in events),
                          'stone_colours': 'per_track_samples' if colours else 'unavailable',
                          'verified_settled_boards': 0, 'physical_identity_verified': False},
              'provenance': {'settings': settings, 'code_sha256': digest(__file__),
                             'input_sha256': {'observations': digest(public_run/'match-observations.jsonl'),
                                              'states': digest(states), 'config': digest(config_path),
                                              'match_config': digest(match_config),
                                              **({'aggregate': digest(aggregate)} if aggregate else {}),
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
    parser.add_argument('--aggregate')
    parser.add_argument('--video')
    args = parser.parse_args()
    print(json.dumps(run(**vars(args))['summary']))
