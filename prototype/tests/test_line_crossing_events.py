import pytest
from prototype.line_crossing_events import LineCrossings,validate_config


def settings():
    return {'schema_version':'stone-line-events-v1','sample_hz':10,'detector_confidence':.1,
            'tracker_config':'bytetrack.yaml','lines':[{'id':'gate','endpoints_normalized':[[.1,.5],[.9,.5]],'direction':'both','deadband_normalized':0}]}


def obs(y,x=.5,track_id=1):return [{'track_id':track_id,'point_normalized':[x,y],'confidence':.9}]


def test_crosses_both_directions_with_observed_time_bracket():
    for before,after,direction in [(.6,.4,'negative'),(.4,.6,'positive')]:
        d=LineCrossings(settings());assert not d.update(obs(before),1)
        e=d.update(obs(after),2)[0]
        assert e['direction']==direction and e['crossing_time_s']==pytest.approx(1.5)
        assert e['observed_bracket_s']==[1,2] and e['release_time_s'] is None
        assert not d.update(obs(before),3) # same tracked stone bouncing back is not another delivery


def test_finite_line_does_not_accept_crossing_its_infinite_extension():
    d=LineCrossings(settings());d.update(obs(.6,x=.95),1);assert not d.update(obs(.4,x=.95),2)


def test_missing_observation_does_not_bridge_crossing():
    d=LineCrossings(settings());d.update(obs(.6),1);d.update([],2);assert not d.update(obs(.4),3)


def test_touching_line_is_not_crossing_but_passing_through_it_is():
    d=LineCrossings(settings());d.update(obs(.6),1);assert not d.update(obs(.5),2);assert not d.update(obs(.6),3)
    d.update(obs(.5),4);assert len(d.update(obs(.4),5))==1


def test_configured_direction_and_two_stones():
    cfg=settings();cfg['lines'][0]['direction']='negative';d=LineCrossings(cfg)
    d.update(obs(.6)+obs(.4,track_id=2),1)
    e=d.update(obs(.4)+obs(.6,track_id=2),2)
    assert len(e)==1 and e[0]['track_id']==1


def test_player_motion_is_not_an_event_filter_input():
    d=LineCrossings(settings());d.update(obs(.6),1)
    observations=obs(.4);observations[0]['surrounding_changed_pixels']=100000
    assert len(d.update(observations,2))==1


def test_no_cross_track_time_suppression():
    d=LineCrossings(settings());d.update(obs(.6)+obs(.6,x=.6,track_id=2),1)
    assert len(d.update(obs(.4)+obs(.4,x=.6,track_id=2),2))==2


@pytest.mark.parametrize('line',[{'endpoints_normalized':[[0,0],[0,0]]},{'endpoints_normalized':[[0,0],[2,1]]},{'deadband_normalized':-1},{'direction':'up'},{'unknown':1}])
def test_invalid_line_rejected(line):
    cfg=settings();cfg['lines'][0].update(line)
    with pytest.raises(ValueError):validate_config(cfg)
