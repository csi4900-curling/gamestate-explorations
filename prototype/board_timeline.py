"""Chunked, frame-indexed storage for observed board states; no interpolation."""
import json
from pathlib import Path


class BoardTimeline:
    # Storage batching only; neither a sampling nor inference parameter.
    chunk_size = 256

    def __init__(self, output):
        self.output = Path(output)
        self.output.mkdir(parents=True)
        self.pending = []
        self.times = []
        self.chunks = 0

    def append(self, state, raw):
        if self.times and state['time_s'] <= self.times[-1]:
            raise ValueError('Board timeline must be strictly chronological')
        boards = {}
        for panel, board in state['boards'].items():
            original = {s.get('tracker_id'): s for s in raw['boards'][panel]['stones']}
            stones = []
            for s in board['stones']:
                height = s.get('position_m') or [None, None]
                plane = original.get(s['tracker_id'], {}).get('ice_plane_local_m') or [None, None]
                stones.append([s['tracker_id'], *s['pixel'], *height, s['group'], *plane])
            boards[panel] = {
                'stones': stones,
                'detected_throw_score': ({k: v for k, v in board['detected_throw_score'].items()
                    if k in ('estimated_points', 'observed_only_points', 'status', 'entries',
                             'stale_event_ids', 'unresolved', 'excluded_unmatched_tracker_ids')}
                    if board.get('detected_throw_score') else None),
                'conditional_visible_board_points': board['conditional_visible_board_points'],
                'unobserved_previously_received_tracker_ids': board['unobserved_previously_received_tracker_ids'],
                'observed_but_not_retained_received_tracker_ids': board['observed_but_not_retained_received_tracker_ids'],
                # Historical evidence stays outside the current solid-dot layer.
                'last_seen': board['last_observed_unretained_receiving_tracks'],
            }
        self.pending.append({'time_s': state['time_s'], 'frame_index': state['frame_index'],
                             'boards': boards, 'end_context': state['end_context'],
                             'unassigned_detected_events': state.get('unassigned_detected_events', []),
                             'last_observed_totals': state['last_observed_totals']})
        self.times.append(state['time_s'])
        if len(self.pending) == self.chunk_size:
            self.flush()

    def flush(self):
        if not self.pending:
            return
        (self.output / f'{self.chunks}.js').write_text(
            f'window.receiveBoardState({self.chunks},' +
            json.dumps(self.pending, separators=(',', ':'), allow_nan=False) + ');\n')
        self.chunks += 1
        self.pending = []

    def finish(self, protocol):
        self.flush()
        return {'times': self.times, 'chunk_size': self.chunk_size, 'chunks': self.chunks,
                'sample_step_s': protocol['sample_step_frames'] / protocol['source_fps'],
                'source_interval_s': protocol['source_interval_s'],
                'stone_columns': ['tracker_id', 'source_x_px', 'source_y_px',
                                  'height_adjusted_x_m', 'height_adjusted_y_m', 'group',
                                  'ice_plane_x_m', 'ice_plane_y_m'],
                'semantics': 'Previous observed frame only; never interpolate stones or carry current detections through missing rows.'}
