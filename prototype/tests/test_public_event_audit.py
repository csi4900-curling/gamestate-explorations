import pytest
from prototype.public_event_audit import verify_scan


def events():
    return dict(status='development_complete_event_stage', source_fps=30,
                source_interval_s=[10, 10.3], sample_step_frames=3, sampled_frames=3)


def rows(frames):
    return [dict(frame_index=f, time_s=f / 30) for f in frames]


def test_verifies_entire_requested_sampling_grid():
    assert verify_scan(events(), rows([300, 303, 306]))['complete_requested_scan']


@pytest.mark.parametrize('frames', [[300, 303], [300, 300, 306], [300, 306, 303], [300, 303, 306, 309]])
def test_rejects_truncated_duplicate_reordered_or_extra_rows(frames):
    with pytest.raises(ValueError):
        verify_scan(events(), rows(frames))


def test_final_status_and_timestamps_are_not_blindly_trusted():
    bad = events()
    bad['status'] = 'running'
    with pytest.raises(ValueError):
        verify_scan(bad, rows([300, 303, 306]))
    data = rows([300, 303, 306])
    data[-1]['time_s'] = 0
    with pytest.raises(ValueError):
        verify_scan(events(), data)
