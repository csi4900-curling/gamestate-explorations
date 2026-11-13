from prototype.spin.throws import event_source_time


def test_failed_tracks_keep_event_time_instead_of_intro():
    assert event_source_time({'event_prediction':{'crossing_time_s':725.83},'segments':[]})==725.83


def test_legacy_event_uses_first_source_observation():
    event={'segments':[{'pixel_points':[{'time_s':750}]},{'pixel_points':[{'time_s':724}]}]}
    assert event_source_time(event)==724
    assert event_source_time({'segments':[]}) is None
