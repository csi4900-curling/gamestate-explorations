"""Conditional board points from existing receiving-track/colour evidence.

No new tracking, calibration or physical identity is inferred. In particular a
near-house stored stone is not assigned to a team just because it was detected.
Missing earlier receiving tracks remain explicit instead of becoming zero.
Settlement must be supplied by a separate observed/estimated-state component.
"""
from prototype.house_points import points_lying
from prototype.detected_throw_score import estimate as estimate_detected_throws


class BoardStateEvidence:
    def __init__(self, events, colours, *, group_to_team, house_radius_m, stone_radius_m):
        if len(group_to_team) != 2 or len(set(group_to_team.values())) != 2:
            raise ValueError('Two distinct colour/team assignments are required')
        self.mapping = dict(group_to_team)
        self.house_radius = house_radius_m
        self.stone_radius = stone_radius_m
        colour_by_id = {r['event_id']: r for r in colours}
        self.receivers = {'left': [], 'right': []}
        self.unassigned_events = []
        for event in events:
            colour = colour_by_id.get(event['candidate_id'], {})
            receivers = [segment for segment in event['segments']
                         if segment.get('role') == 'receiving' and segment.get('pixel_points')]
            if len(receivers) != 1:
                self.unassigned_events.append({'event_id': event['candidate_id'],
                    'crossing_time_s': event['event_prediction']['crossing_time_s'],
                    'reason': 'missing_or_ambiguous_receiving_assignment'})
            for segment in event['segments']:
                if segment.get('role') != 'receiving' or not segment.get('pixel_points'):
                    continue
                panel = segment.get('rink_panel') or {'left_split':'left', 'right_split':'right'}.get(segment['camera'])
                if panel not in self.receivers:
                    raise ValueError('Receiving panel is undefined')
                self.receivers[panel].append({
                    'event_id': event['candidate_id'], 'tracker_id': segment['tracker_id'],
                    'crossing_time_s': event['event_prediction']['crossing_time_s'],
                    'association_ambiguous': len(receivers) != 1,
                    'available_after_s': max(event['event_prediction']['crossing_time_s'],
                                             segment['pixel_points'][0]['time_s']),
                    'group': colour.get('colour'), 'colour_status': colour.get('colour_status'),
                    'basis': 'Existing receiving segment and event-crop colour; camera/physical identity provisional',
                    'physical_identity_verified': False,
                })

    def observe(self, observation, *, settlement=None, end_context=None, track_memory=None):
        result = {'time_s':observation['time_s'], 'frame_index':observation['frame_index'],
                  'settlement':settlement or {'status':'unknown', 'basis':'Settlement not evaluated'},
                  'group_to_team':self.mapping, 'team_mapping_status':'supplied_metadata',
                  'physical_board_verified':False, 'official_end_score':None, 'boards':{}}
        result['end_context'] = end_context
        epoch_start = (end_context or {}).get('epoch_start_s', float('-inf'))
        result['unassigned_detected_events'] = [event for event in self.unassigned_events
            if epoch_start <= event['crossing_time_s'] <= observation['time_s']]
        for panel, board in observation['boards'].items():
            epoch_start = (end_context or {}).get('epoch_start_s', float('-inf'))
            available = [x for x in self.receivers[panel]
                         if epoch_start <= x['available_after_s'] <= observation['time_s']]
            visible_tracks = {s.get('tracker_id') for s in board['stones'] if s.get('tracker_id') is not None}
            missing = sorted({x['tracker_id'] for x in available if x['tracker_id'] not in visible_tracks})
            last_known = []; observed_not_retained = []
            for tracker_id in missing:
                previous = (track_memory or {}).get(panel, {}).get(tracker_id)
                # Never reuse future or pre-delivery observations of a track ID.
                earliest = min(x['available_after_s'] for x in available if x['tracker_id'] == tracker_id)
                if previous is None or not earliest <= previous['time_s'] <= observation['time_s']:
                    continue
                observed_now = previous['frame_index'] == observation['frame_index']
                if observed_now: observed_not_retained.append(tracker_id)
                last_known.append({**previous, 'tracker_id': tracker_id,
                                   'age_s': observation['time_s']-previous['time_s'],
                                   'status': ('observed_but_not_retained' if observed_now
                                              else 'last_observed_not_current_position'),
                                   'currently_observed': observed_now,
                                   'retained_in_current_board': False,
                                   'physical_identity_verified': False})
            inputs = []; evidence = []
            for i, stone in enumerate(board['stones']):
                matches = [x for x in available if x['tracker_id'] == stone.get('tracker_id')]
                groups = {x['group'] for x in matches}
                group = next(iter(groups)) if len(matches)==1 and len(groups)==1 else None
                if group not in self.mapping:
                    group = None
                inputs.append({'observation_id':f'{panel}:{i}', 'group':group,
                               'position_m':stone.get('height_adjusted_local_m')})
                evidence.append({'observation_id':f'{panel}:{i}', 'tracker_id':stone.get('tracker_id'),
                                 'pixel':stone['pixel'], 'position_m':stone.get('height_adjusted_local_m'),
                                 'group':group, 'receiving_track_evidence':matches,
                                 'in_play_status':'provisional_received_track' if matches else 'unknown_no_receiving_track_evidence',
                                 'physical_identity_verified':False})
            score = points_lying(inputs, house_radius_m=self.house_radius,
                                 stone_radius_m=self.stone_radius, groups=list(self.mapping))
            by_group = score['conditional_points_by_group']
            conditional = ({self.mapping[g]:v for g,v in by_group.items()} if by_group is not None else None)
            supported = (result['settlement']['status'] in ('observed_settled', 'estimated_settled')
                         and not missing and conditional is not None)
            subset_available = [x for x in self.receivers[panel]
                                if epoch_start <= x['crossing_time_s'] <= observation['time_s']]
            subset = estimate_detected_throws(subset_available, evidence, last_known,
                mapping=self.mapping, house_radius_m=self.house_radius,
                stone_radius_m=self.stone_radius)
            subset['end_context'] = end_context
            for entry in subset['entries']:
                if entry['position_status'] == 'currently_observed':
                    entry['observed_at_s'] = observation['time_s']
            result['boards'][panel] = {
                'detected_throw_score': subset,
                'stones':evidence, 'conditional_visible_board_points':conditional,
                'post_throw_points':conditional if supported else None,
                'unobserved_previously_received_tracker_ids':[i for i in missing if i not in observed_not_retained],
                'observed_but_not_retained_received_tracker_ids':observed_not_retained,
                'last_observed_unretained_receiving_tracks':last_known,
                'points_evidence':score,
                'status':'conditional_post_throw_estimate' if supported else 'incomplete_state_evidence',
                'limitations':['Track labels and event colours do not establish physical identity.',
                               'Missing earlier tracks are not assumed removed or absent from the house.',
                               'No duplicate suppression or full-board completeness validation is added here.',
                               'Conditional points depend on supplied geometry, in-play membership and team metadata.'],
            }
        return result
