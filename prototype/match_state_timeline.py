"""Assemble saved board and scoreboard evidence without claiming complete game state.

Development postprocessing; no detector, association or geometry changes.
"""
import argparse
from bisect import bisect_right
import hashlib
import json
from pathlib import Path

from prototype.score_grid import parse_end_cells
from prototype.score_sequence import infer


def assemble(boards, scores, teams, colour_observations=(), *, score_layout_memory=False):
    """Yield synchronized evidence; never use a later reading as an observation."""
    layout = None
    if score_layout_memory:
        from prototype.score_layout_memory import infer as infer_layout, chronological_layout_scores
        layout = list(infer_layout(scores, teams))
        chronology = chronological_layout_scores(layout)
    else:
        chronology = infer(scores)
    times = [r['time_s'] for r in scores]
    last = {}
    consumed = 0
    previous_time = None
    colours = list(colour_observations)
    if any(b['time_s'] < a['time_s'] for a, b in zip(colours, colours[1:])):
        raise ValueError('Colour observations must be chronological')
    if any(r['team'] not in teams for r in colours):
        raise ValueError('Unknown team in colour observations')
    colour_index = 0
    colour_history = {team: [] for team in teams}
    for board in boards:
        t = board['time_s']
        if previous_time is not None and t <= previous_time:
            raise ValueError('Board observations must be strictly chronological')
        previous_time = t
        while colour_index < len(colours) and colours[colour_index]['time_s'] <= t:
            observation = colours[colour_index]
            colour_history[observation['team']].append(observation)
            colour_index += 1
        colour_evidence = {}
        for team, history in colour_history.items():
            seen = sorted({r['predicted_background_colour'] for r in history})
            colour_evidence[team] = {
                'status': 'unknown' if not history else 'conflicting_observations' if len(seen) > 1 else 'background_colour_hypothesis',
                'background_colour_hypothesis': seen[0] if len(seen) == 1 else None,
                'observed_colours': seen,
                'last_observation': {**history[-1], 'age_s': t-history[-1]['time_s']} if history else None,
                'observation_count': len(history),
                'stone_team_mapping_verified': False,
                'future_observations_used': False,
            }
        index = bisect_right(times, t) - 1
        while consumed <= index:
            row = scores[consumed]
            for team in teams:
                reading = row['totals'].get(team, {})
                if reading.get('value') is not None:
                    last[team] = dict(value=reading['value'], observed_at_s=row['time_s'],
                                      source_observation_index=consumed)
            consumed += 1
        latest = scores[index] if index >= 0 else None
        parsed = parse_end_cells(latest.get('tokens', []), teams) if latest else None
        # A prior active-end marker may already be stale. Do not carry it forward
        # as a current-end measurement without an end-transition model.
        displayed_end = parsed['current_end'] if parsed else None
        totals = {}
        for team in teams:
            observed = latest['totals'].get(team, {}).get('value') if latest and latest['time_s'] == t else None
            totals[team] = {
                'observed_at_this_time': observed,
                'last_reading': {**last[team], 'age_s': t-last[team]['observed_at_s'],
                                 'status': 'ocr_observed_unverified'} if team in last else None,
                'offline_inferred': None,
            }
            if layout is not None:
                totals[team]['layout_inferred_at_this_time'] = (
                    layout[index]['layout_inferred_totals'][team]
                    if index >= 0 and latest['time_s'] == t else None)
            if index >= 0:
                value = chronology['timeline'][index]['totals'].get(team, {})
                if value.get('value') is not None:
                    totals[team]['offline_inferred'] = {
                        **value, 'age_s': t-value['observed_at_s'],
                        'future_observations_used': True,
                    }
        yield {
            'time_s': t, 'frame_index': board.get('frame_index'),
            'boards': board['boards'],
            'board_semantics': 'Camera panels; physical ends and identities remain as supplied, not inferred from panel names.',
            'cumulative_match_score': totals,
            'scoreboard_team_colour_evidence': colour_evidence,
            'score_stream_semantics': 'Cumulative fields above use the supplied scoreboard stream. Public-run OCR below is retained separately; streams are not silently substituted or merged.',
            'public_run_score_evidence': {
                'observation': board.get('score_observation'),
                'last_observed_totals': board.get('last_observed_totals', {}),
                'current_end': board.get('current_end'),
                'current_points_from_stones': board.get('current_points_from_stones'),
            },
            'latest_score_observation_index': index if index >= 0 else None,
            'latest_score_observation_age_s': t-latest['time_s'] if latest else None,
            'current_end': None,
            'current_end_provenance': 'unknown: displayed scoreboard can lag physical play',
            'displayed_end_evidence': ({
                'value': displayed_end, 'observed_at_s': latest['time_s'],
                'age_s': t-latest['time_s'],
                'observed_at_this_time': latest['time_s'] == t,
                'status': 'scoreboard_marker_observed_unverified',
                'evidence': parsed.get('current_end_evidence'),
                'physical_end_verified': False,
            } if displayed_end is not None else None),
            'latest_scoreboard_parse': parsed,
            'current_points_in_house': None,
            'current_points_status': 'unknown: team identity, in-play classification and complete board not established',
            'complete_match_state_verified': False,
        }


def run(public_run, score_observations, output, teams, colour_observations=None, *, score_layout_memory=False):
    public_run, score_observations, output = map(Path, (public_run, score_observations, output))
    source = json.loads((public_run/'events.json').read_text())['source_sha256']
    protocol = json.loads((score_observations.parent/'protocol.json').read_text())
    if source != protocol['source_sha256']:
        raise ValueError('Board and scoreboard source hashes differ')
    colour_rows = []
    if colour_observations is not None:
        colour_observations = Path(colour_observations)
        colour_data = json.loads(colour_observations.read_text())
        if colour_data['source_sha256'] != source:
            raise ValueError('Colour and board source hashes differ')
        colour_rows = colour_data['observations']
    if output.exists():
        raise ValueError('Preserve previous state outputs')
    scores = [json.loads(line) for line in score_observations.open()]
    board_path = public_run/'match-observations.jsonl'
    output.mkdir(parents=True)
    count = 0
    with board_path.open() as inp, (output/'timeline.jsonl').open('w') as out:
        for row in assemble((json.loads(line) for line in inp), scores, teams, colour_rows,
                            score_layout_memory=score_layout_memory):
            out.write(json.dumps(row, allow_nan=False)+'\n')
            count += 1
    def sha(path):
        h = hashlib.sha256()
        with Path(path).open('rb') as stream:
            for block in iter(lambda: stream.read(1024*1024), b''):
                h.update(block)
        return h.hexdigest()
    manifest = dict(development=True, samples=count, source_sha256=source,
                    inputs={str(p.resolve()): sha(p) for p in [board_path, public_run/'events.json', score_observations, score_observations.parent/'protocol.json']},
                    code={name: sha(Path(__file__).with_name(name)) for name in ['match_state_timeline.py', 'score_sequence.py', 'score_grid.py']},
                    teams=teams, inference_pipeline_changed=score_layout_memory,
                    score_layout_memory_enabled=score_layout_memory,
                    limitations=['Offline score inference uses future observations and assumes nondecreasing totals in one live match.',
                                 'OCR errors, replays and post-match resets are not classified.',
                                 'No team/stone identity, in-play classification, end transitions or points in the house inferred.',
                                 'This evidence assembly is not complete match-state accuracy.'])
    if score_layout_memory:
        manifest['code']['score_layout_memory.py'] = sha(Path(__file__).with_name('score_layout_memory.py'))
        manifest['limitations'].append('Missing team-score attribution may be inferred from previous OCR layout; source_attribution distinguishes it from direct OCR. No new detector, geometry or identity inference is performed.')
    for name in manifest['code']:
        (output/name).write_bytes(Path(__file__).with_name(name).read_bytes())
    if colour_observations is not None:
        manifest['inputs'][str(colour_observations.resolve())] = sha(colour_observations)
        manifest['limitations'].append('Timestamped scoreboard background colours are hypotheses, not verified stone-to-team assignments; conflicting colours are retained.')
    (output/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', required=True)
    parser.add_argument('--score-observations', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--teams', nargs=2, required=True)
    parser.add_argument('--colour-observations')
    parser.add_argument('--score-layout-memory', action='store_true', help='Development offline score composition with explicit layout provenance; default disabled')
    args = parser.parse_args()
    print(json.dumps(run(args.run, args.score_observations, args.output, args.teams, args.colour_observations,
                         score_layout_memory=args.score_layout_memory)))
