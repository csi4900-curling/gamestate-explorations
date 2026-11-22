"""End segmentation, running score comparison, and rule-based rock-slot analytics.

Groups throws into ends using sustained direction reversals (left->right vs
right->left), compares provisional end-of-end house points against OCR scoreboard
readings (keeping missing OCR explicitly unknown), and summarizes trajectory
kinematics by Team + Rule-Based Rock Pair (1-2 Lead, 3-4 Second, 5-6 Third,
7-8 Fourth/Skip). Handle numbers are not readable at 1080p split-screen scale;
rock-slot provenance is explicitly recorded as rule-based delivery order.
"""
import argparse
import json
import math
from pathlib import Path
from statistics import median

from prototype.detection_cache import digest

ROCK_PAIRS = (
    (1, 2, '1-2 (Lead)'),
    (3, 4, '3-4 (Second)'),
    (5, 6, '5-6 (Third)'),
    (7, 8, '7-8 (Fourth/Skip)'),
)


def rock_pair_label(team_slot):
    if team_slot is None or team_slot < 1:
        return None
    for lo, hi, label in ROCK_PAIRS:
        if lo <= team_slot <= hi:
            return label
    return f'{team_slot}+ (Extra/Overflow)'


def throw_direction(agg_event, eff_event):
    """Return 'left_to_right', 'right_to_left', or None from observed camera roles."""
    dep_panels = {
        s.get('rink_panel') or {'left_split': 'left', 'right_split': 'right'}[s['camera']]
        for s in agg_event.get('segments', [])
        if s.get('role') == 'departure'
    }
    rec_panels = {
        s.get('rink_panel') or {'left_split': 'left', 'right_split': 'right'}[s['camera']]
        for s in agg_event.get('segments', [])
        if s.get('role') == 'receiving'
    }
    if not rec_panels and eff_event and eff_event.get('panel') in ('left', 'right'):
        rec_panels = {eff_event['panel']}
    if dep_panels == {'left'} or rec_panels == {'right'}:
        return 'left_to_right'
    if dep_panels == {'right'} or rec_panels == {'left'}:
        return 'right_to_left'
    return None


def segment_ends(throws, max_throws_per_end=16):
    """Segment chronologically ordered throws into ends using sustained direction reversals."""
    if not throws:
        return []
    # Smooth isolated single-throw direction glitches: a real end reversal
    # persists for at least 2 throws (or is the final throw of the clip).
    dirs = [t['direction'] for t in throws]
    end_idx = 1
    current_dir = next((d for d in dirs if d is not None), None)
    count_in_end = 0
    assigned = []
    for i, item in enumerate(throws):
        d = item['direction']
        if d is not None and current_dir is not None and d != current_dir:
            # Confirm reversal if next known direction also matches d, OR current end already has >= 10 throws.
            future = [x for x in dirs[i + 1:i + 4] if x is not None]
            confirmed = (future and future[0] == d) or count_in_end >= 10 or (not future and count_in_end >= 4)
            if confirmed:
                end_idx += 1
                current_dir = d
                count_in_end = 0
        elif count_in_end >= max_throws_per_end and item.get('board_status') != 'unresolved':
            end_idx += 1
            count_in_end = 0
            if d is not None:
                current_dir = d
        if item.get('board_status') != 'unresolved':
            count_in_end += 1
        assigned.append(end_idx)
    return assigned


def throw_kinematics(agg_event, eff_event):
    """Compute receiving-view speed and lateral curl displacement on mapped samples."""
    rec_segs = [s for s in agg_event.get('segments', []) if s.get('role') == 'receiving']
    if len(rec_segs) != 1:
        return None
    pts = [p for p in rec_segs[0].get('geometry_samples', []) if p.get('rink_position_m') is not None]
    if len(pts) < 4:
        return None
    # Restrict to before settle start if available.
    if eff_event and eff_event.get('settle_interval_s'):
        stop_t = eff_event['settle_interval_s'][0]
        pts = [p for p in pts if p['time_s'] <= stop_t]
    if len(pts) < 4:
        return None
    t0, p0 = pts[0]['time_s'], pts[0]['rink_position_m']
    t1, p1 = pts[-1]['time_s'], pts[-1]['rink_position_m']
    dt = t1 - t0
    if dt <= 0.3:
        return None
    dist = math.hypot(p1[0] - p0[0], p1[1] - p0[1])
    # Lateral curl: deviation from initial heading vector (first 1.0s) to final position.
    early = [p for p in pts if p['time_s'] <= t0 + 1.0]
    if len(early) < 2:
        early = pts[:2]
    pe = early[-1]['rink_position_m']
    vx, vy = pe[0] - p0[0], pe[1] - p0[1]
    vnorm = math.hypot(vx, vy)
    lateral_m = None
    if vnorm >= 0.3:
        # Signed perpendicular distance from initial velocity ray to final point (metres).
        dx, dy = p1[0] - p0[0], p1[1] - p0[1]
        lateral_m = (vx * dy - vy * dx) / vnorm
    return {
        'receiving_observed_duration_s': round(dt, 2),
        'receiving_path_chord_m': round(dist, 2),
        'receiving_mean_speed_m_s': round(dist / dt, 2),
        'lateral_curl_m': round(lateral_m, 3) if lateral_m is not None else None,
        'mapped_samples': len(pts),
    }


def _ocr_readings(score_obs_path):
    path = Path(score_obs_path)
    if not path.exists():
        return []
    rows = []
    with path.open() as stream:
        for line in stream:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def _ocr_snapshot_after(ocr_rows, after_t, before_t, team_labels):
    """Return latest OCR reading with valid totals or end cells between after_t and before_t."""
    candidates = [r for r in ocr_rows if after_t <= r['time_s'] <= before_t]
    for r in reversed(candidates):
        totals = {team: (r.get('totals') or {}).get(team, {}).get('value') for team in team_labels}
        if any(v is not None for v in totals.values()):
            return {
                'time_s': r['time_s'],
                'totals': totals,
                'displayed_end': r.get('displayed_end'),
                'status': 'ocr_observed_unverified',
            }
    return None


def build(*, aggregate, effects, state_config, score_observations=None, revolutions=None, output=None):
    agg = json.loads(Path(aggregate).read_text())
    eff = json.loads(Path(effects).read_text())
    state_cfg = json.loads(Path(state_config).read_text())
    group_to_team = state_cfg.get('group_to_team', {'red': 'RED', 'yellow': 'YELLOW'})
    team_labels = [group_to_team.get('red', 'RED'), group_to_team.get('yellow', 'YELLOW')]

    agg_by_id = {e['candidate_id']: e for e in agg['events']}
    eff_by_id = {e['event_id']: e for e in eff['events']}
    rev_by_id = {}
    if revolutions and Path(revolutions).exists():
        rev_by_id = {e['event_id']: e for e in json.loads(Path(revolutions).read_text()).get('events', [])}
    ocr_rows = _ocr_readings(score_observations) if score_observations else []

    ordered_ids = [e['event_id'] for e in sorted(eff['events'], key=lambda x: x['crossing_time_s'])]
    raw_throws = []
    for eid in ordered_ids:
        ae = agg_by_id.get(eid, {})
        ee = eff_by_id[eid]
        # Prefer delivered stone's unanimous track colour, fall back to event colour.
        delivered_colour = None
        for st in ee.get('stones', []):
            if st.get('change') == 'delivered' and not st.get('colour_differs_along_track'):
                delivered_colour = st.get('colour')
                break
        if delivered_colour is None and ae.get('colour') in ('red', 'yellow'):
            delivered_colour = ae['colour']
        raw_throws.append({
            'event_id': eid,
            'crossing_time_s': ee['crossing_time_s'],
            'direction': throw_direction(ae, ee),
            'colour': delivered_colour,
            'team': group_to_team.get(delivered_colour) if delivered_colour else None,
            'board_status': ee['status'],
            'points_lying_after': ee.get('points_lying_after'),
            'kinematics': throw_kinematics(ae, ee),
            'spin_rate_hz': ((rev_by_id.get(eid, {}).get('sending') or {}).get('rate_hz')
                             or (rev_by_id.get(eid, {}).get('receiving') or {}).get('rate_hz')),
        })

    end_numbers = segment_ends(raw_throws)
    ends_map = {}
    for item, end_num in zip(raw_throws, end_numbers):
        end_entry = ends_map.setdefault(end_num, {
            'end_index': end_num,
            'direction': item['direction'],
            'throws': [],
            'team_counts': {'red': 0, 'yellow': 0},
        })
        if end_entry['direction'] is None and item['direction'] is not None:
            end_entry['direction'] = item['direction']
        team_slot = None
        if item.get('board_status') != 'unresolved' and item['colour'] in ('red', 'yellow'):
            end_entry['team_counts'][item['colour']] += 1
            team_slot = end_entry['team_counts'][item['colour']]
        item['end_index'] = end_num
        item['throw_in_end'] = len(end_entry['throws']) + 1
        item['team_slot'] = team_slot
        item['rock_pair'] = rock_pair_label(team_slot)
        item['rock_slot_provenance'] = (
            'Rule-based rock-pair assignment from delivery order within inferred end; '
            'engraved handle numbers are not readable at 1080p.'
        )
        end_entry['throws'].append(item)

    # Assemble per-end board score vs OCR score and running totals.
    ends_list = []
    running_board = {team: 0 for team in team_labels}
    end_keys = sorted(ends_map)
    for pos, end_num in enumerate(end_keys):
        ed = ends_map[end_num]
        last_t = ed['throws'][-1]['crossing_time_s']
        next_t = ends_map[end_keys[pos + 1]]['throws'][0]['crossing_time_s'] if pos + 1 < len(end_keys) else last_t + 300.0
        # Final resolved throw in this end gives provisional board points.
        board_pts = None
        board_source_event = None
        for th in reversed(ed['throws']):
            pts = (th.get('points_lying_after') or {}).get('conditional_points_by_group')
            if pts is not None:
                board_pts = {group_to_team.get(g, g): int(v) for g, v in pts.items()}
                board_source_event = th['event_id']
                break
        if board_pts is not None:
            for team in team_labels:
                running_board[team] += board_pts.get(team, 0)
        ocr_snap = _ocr_snapshot_after(ocr_rows, last_t, next_t + 180.0, team_labels)
        ends_list.append({
            'end_index': end_num,
            'direction': ed['direction'],
            'detected_throws': len(ed['throws']),
            'event_ids': [t['event_id'] for t in ed['throws']],
            'time_span_s': [round(ed['throws'][0]['crossing_time_s'], 1), round(last_t, 1)],
            'provisional_end_score_from_board': board_pts,
            'provisional_board_source_event': board_source_event,
            'provisional_running_total_from_board': dict(running_board),
            'ocr_running_total_observation': ocr_snap,
            'score_status': 'provisional_board_and_unverified_ocr',
        })

    # Aggregate cross-end rock-pair behavior (for Canada team rock comparison).
    rock_groups = {}
    for th in raw_throws:
        if not th['team'] or not th['rock_pair']:
            continue
        key = (th['colour'], th['team'], th['rock_pair'])
        g = rock_groups.setdefault(key, {
            'colour': th['colour'],
            'team': th['team'],
            'rock_pair': th['rock_pair'],
            'throws': 0,
            'ends_seen': [],
            'speeds': [],
            'abs_curls': [],
            'signed_curls': [],
            'spin_rates': [],
            'event_ids': [],
        })
        g['throws'] += 1
        if th['end_index'] not in g['ends_seen']:
            g['ends_seen'].append(th['end_index'])
        g['event_ids'].append(th['event_id'])
        kin = th.get('kinematics') or {}
        if kin.get('receiving_mean_speed_m_s') is not None:
            g['speeds'].append(kin['receiving_mean_speed_m_s'])
        if kin.get('lateral_curl_m') is not None:
            g['signed_curls'].append(kin['lateral_curl_m'])
            g['abs_curls'].append(abs(kin['lateral_curl_m']))
        if th.get('spin_rate_hz') is not None:
            g['spin_rates'].append(th['spin_rate_hz'])

    rock_summary = []
    for key in sorted(rock_groups):
        g = rock_groups[key]
        rock_summary.append({
            'colour': g['colour'],
            'team': g['team'],
            'rock_pair': g['rock_pair'],
            'throws_observed': g['throws'],
            'ends_seen': g['ends_seen'],
            'event_ids': g['event_ids'],
            'median_receiving_speed_m_s': round(median(g['speeds']), 2) if g['speeds'] else None,
            'median_abs_curl_m': round(median(g['abs_curls']), 3) if g['abs_curls'] else None,
            'median_signed_curl_m': round(median(g['signed_curls']), 3) if g['signed_curls'] else None,
            'median_spin_rate_hz': round(median(g['spin_rates']), 3) if g['spin_rates'] else None,
            'provenance': 'Rule-based rock-pair grouping by delivery order within inferred end; physical rock numbers not visually verified.',
        })

    payload = {
        'schema_version': 'curling-match-score-and-rocks-development-v1',
        'development': True,
        'source_sha256': eff['source_sha256'],
        'teams': team_labels,
        'group_to_team': group_to_team,
        'ends': ends_list,
        'throws': raw_throws,
        'rock_pair_summary': rock_summary,
        'summary': {
            'inferred_ends': len(ends_list),
            'total_throws': len(raw_throws),
            'provisional_final_total_from_board': running_board,
            'official_scoring_verified': False,
            'physical_rock_identity_verified': False,
        },
        'provenance': {
            'code_sha256': digest(__file__),
            'limitations': [
                'End boundaries are inferred from sustained throw direction reversals; missed throws can shift within-end slot numbers.',
                'Provisional board scores come from each end\'s final resolved throw and are not official match totals.',
                'Rock pairs (1-2, 3-4, 5-6, 7-8) follow World Curling player-pair assignment rules; handle numbers are unreadable at 1080p.',
            ],
        },
    }
    if output is not None:
        Path(output).parent.mkdir(parents=True, exist_ok=True)
        Path(output).write_text(json.dumps(payload, indent=2, allow_nan=False) + '\n')
    return payload


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('aggregate', 'effects', 'state-config', 'output'):
        parser.add_argument('--' + name, required=True)
    parser.add_argument('--score-observations')
    parser.add_argument('--revolutions')
    args = parser.parse_args()
    print(json.dumps(build(
        aggregate=args.aggregate,
        effects=args.effects,
        state_config=args.state_config,
        score_observations=args.score_observations,
        revolutions=args.revolutions,
        output=args.output,
    )['summary']))
