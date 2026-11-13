"""Score an explicit subset of event-associated stones, without new association rules.

Stable ledger keys are detected-event IDs, not a claim of physical identity.
Current tracker observations update positions. Occlusions hold last observations
as estimates with ages; they never establish removal. Unmatched detections are
excluded only from this subset calculation, not from the displayed board.
"""
from prototype.house_points import points_lying


def estimate(available, stones, last_known, *, mapping, house_radius_m, stone_radius_m):
    by_event = {}
    for link in available:
        by_event.setdefault(link['event_id'], []).append(link)
    entries = []
    current_inputs = []
    for event_id, links in by_event.items():
        tracks = {link['tracker_id'] for link in links}
        groups = {link['group'] for link in links}
        current = [s for s in stones if any(x['event_id'] == event_id
                                           for x in s['receiving_track_evidence'])]
        tracker_owners = {x['event_id'] for x in available if x['tracker_id'] in tracks}
        ambiguous = any(link.get('association_ambiguous') for link in links) or len(links) != 1 or len(tracks) != 1 or len(tracker_owners) != 1 or len(current) > 1
        group = next(iter(groups)) if len(groups) == 1 else None
        group = group if group in mapping else None
        entry = {'event_id': event_id, 'team': mapping.get(group), 'group': group,
                 'tracker_ids': sorted(tracks), 'position_m': None, 'observed_at_s': None,
                 'age_s': None, 'position_status': 'never_observed',
                 'physical_identity_verified': False,
                 'identity_basis': 'Existing event-to-receiving-track association; no new relinking'}
        if ambiguous:
            entry['position_status'] = 'ambiguous_event_track_assignment'
        elif current:
            stone = current[0]
            entry.update(position_m=stone['position_m'], position_status='currently_observed', age_s=0.)
            current_inputs.append({'observation_id': event_id, 'group': group,
                                   'position_m': stone['position_m']})
        else:
            previous = [s for s in last_known if s['tracker_id'] in tracks]
            if previous:
                previous = previous[0]
                if previous.get('currently_observed'):
                    entry['position_status'] = 'current_detection_suppressed_unresolved'
                else:
                    entry.update(position_m=previous['position_m'],
                                 observed_at_s=previous['time_s'], age_s=previous['age_s'],
                                 position_status='last_observed_hold_estimate')
        entries.append(entry)
    inputs = [{'observation_id': s['event_id'], 'group': s['group'], 'position_m': s['position_m']}
              for s in entries]
    options = dict(house_radius_m=house_radius_m, stone_radius_m=stone_radius_m, groups=list(mapping))
    score = points_lying(inputs, **options)
    current_score = points_lying(current_inputs, **options)
    points = score['conditional_points_by_group']
    stale = [s['event_id'] for s in entries if s['position_status'] == 'last_observed_hold_estimate']
    return {
        'scope': 'Stones associated with detected throws in the current supplied end epoch',
        'estimated_points': {mapping[g]: v for g, v in points.items()} if points is not None and entries else None,
        'observed_only_points': ({mapping[g]: v for g, v in current_score['conditional_points_by_group'].items()}
                                 if current_score['conditional_points_by_group'] is not None else None),
        'status': ('no_associated_board_state' if not entries else 'unresolved' if points is None else 'estimated_with_last_known_positions' if stale
                   else 'conditional_on_current_associations'),
        'entries': entries, 'stale_event_ids': stale,
        'unresolved': score['unresolved_observations'],
        'excluded_unmatched_tracker_ids': [s['tracker_id'] for s in stones if not s['receiving_track_evidence']],
        'calculation': score,
        'assumptions': ['Existing receiving associations and event colours identify the intended stones.',
                        'Last observed positions are held during gaps; collisions during gaps are not observed.',
                        'Actual positions include effects of unmatched throws; no counterfactual physics is simulated.'],
        'official_end_score': None, 'physical_identity_verified': False,
    }


class DeliveryEndContext:
    """Exact-time version of the existing declared deliveries-per-end inference.

    The final delivery stays in its end throughout travel and settlement. An end
    changes at the next end's first detected crossing, never one sample earlier.
    This is a counter-based estimate, not observed physical end segmentation.
    """
    def __init__(self, events, *, end_size, start_s):
        from bisect import bisect_right
        if not isinstance(end_size, int) or end_size <= 0:
            raise ValueError('Positive integer deliveries per end required')
        self.times = [event['event_prediction']['crossing_time_s'] for event in events]
        if self.times != sorted(self.times):
            raise ValueError('Chronological detected throws required')
        self.end_size, self.start_s, self.bisect_right = end_size, start_s, bisect_right

    def at(self, time_s):
        latest = self.bisect_right(self.times, time_s) - 1
        end_index = max(latest, 0) // self.end_size
        return {'current_end': end_index + 1, 'status': 'inferred_from_delivery_sequence',
                'epoch_start_s': self.times[end_index * self.end_size] if end_index else self.start_s,
                'deliveries_per_end': self.end_size,
                'basis': 'End containing latest detected throw; next end starts at its first crossing.',
                'assumptions': ['Detected candidates are chronological deliveries.',
                                'No missing or extra events for correspondence to physical ends.'],
                'physical_end_verified': False}


def build_match_ledger(events, proposals, *, end_size, teams, start_s):
    """Award each inferred completed end once, using its final throw's result.

    Missing final results remain unresolved. Earlier throws cannot silently
    replace the final throw. End-score snapshots are never added per delivery.
    Video exhaustion alone does not establish that the last end is complete.
    """
    context = DeliveryEndContext(events, end_size=end_size, start_s=start_s)
    by_id = {row['event_id']: row for row in proposals}
    ends = []
    subtotal = dict.fromkeys(teams, 0)
    unresolved = []
    timeline = [{'time_s': start_s, 'known_subtotal': dict(subtotal),
                 'estimated_total': dict(subtotal), 'unresolved_end_numbers': [],
                 'completed_end_numbers': []}]
    for offset in range(0, len(events), end_size):
        group = events[offset:offset + end_size]
        number = offset // end_size + 1
        following = events[offset + end_size:offset + end_size + 1]
        closed_at = following[0]['event_prediction']['crossing_time_s'] if following else None
        last = by_id[group[-1]['candidate_id']]
        proposal = last['proposal']
        state = last.get('state')
        points = None
        reason = 'no_post_throw_result_for_final_detected_throw'
        evidence = None
        if state is not None and proposal.get('panel') and proposal.get('time_s') is not None:
            evidence = state['boards'][proposal['panel']]['detected_throw_score']
            points = evidence['estimated_points']
            if state['end_context']['current_end'] != number:
                points = None
                reason = 'result_belongs_to_different_end_context'
            elif closed_at is not None and proposal['time_s'] >= closed_at:
                points = None
                reason = 'result_after_next_inferred_end_started'
            elif points is None:
                reason = evidence['status']
            else:
                reason = None
        end = {'end_number': number, 'start_s': context.at(group[0]['event_prediction']['crossing_time_s'])['epoch_start_s'],
               'closed_at_s': closed_at, 'boundary_status': 'inferred_from_delivery_sequence',
               'detected_event_ids': [event['candidate_id'] for event in group],
               'final_event_id': group[-1]['candidate_id'],
               'final_event_time_s': group[-1]['event_prediction']['crossing_time_s'],
               'score_observed_at_s': proposal.get('time_s'),
               'estimated_end_points': points,
               'position_status': evidence['status'] if evidence else None,
               'stale_event_ids': evidence['stale_event_ids'] if evidence else [],
               'status': 'open_end_not_awarded' if closed_at is None else 'estimated_end_awarded' if points is not None else 'unresolved_end',
               'unresolved_reason': reason, 'official_end_score': None}
        ends.append(end)
        if closed_at is not None:
            if points is None:
                unresolved.append(number)
            else:
                for team in teams:
                    subtotal[team] += points[team]
            timeline.append({'time_s': closed_at, 'known_subtotal': dict(subtotal),
                             'estimated_total': dict(subtotal) if not unresolved else None,
                             'unresolved_end_numbers': list(unresolved),
                             'completed_end_numbers': list(range(1, number + 1))})
    return {'scope': 'Accumulated estimates for inferred completed ends of the detected-throw reconstruction',
            'deliveries_per_end': end_size, 'ends': ends, 'timeline': timeline,
            'official_match_score': None, 'physical_end_boundaries_verified': False,
            'initial_score_basis': 'Reconstruction starts from zero at analysed interval; not an observed prior match total.',
            'limitations': ['End assignment inherits the declared deliveries-per-end assumption, not OCR scores.',
                           'Held positions and identity errors propagate into estimated end points.',
                           'Unresolved ends are not zero and are excluded only from the explicitly labelled known subtotal.',
                           'The last end remains open without evidence of completion.']}
