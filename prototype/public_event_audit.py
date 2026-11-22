"""Verify saved observation streams cover the exact requested frame grid."""


def verify_scan(events, observations):
    if events['status'] != 'development_complete_event_stage':
        raise ValueError('Event stage is not finalized')
    fps = events['source_fps']
    first, stop = [round(t * fps) for t in events['source_interval_s']]
    expected = range(first, stop, events['sample_step_frames'])
    obs_iter = iter(observations)
    count = 0
    for expected_frame, row in zip(expected, obs_iter):
        if row['frame_index'] != expected_frame:
            raise ValueError('Incomplete scan: unexpected sampled frame')
        if abs(row['time_s'] - expected_frame / fps) > 1e-9:
            raise ValueError('Source time does not match frame index')
        count += 1
    if count != len(expected) or count != events['sampled_frames'] or next(obs_iter, None) is not None:
        raise ValueError('Incomplete scan: saved frame coverage differs from requested interval')
    return dict(expected_sampled_frames=len(expected), verified_sampled_frames=count,
                source_interval_s=events['source_interval_s'], complete_requested_scan=True)
