import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from span_passage_detection import SpanPassageDetector


def observation(y, x=160, colour="red"):
    return {"colour": colour, "pixel": [x, y], "bbox": [x - 4, y - 4, 8, 8], "body_support": 1.0}


def test_detects_stone_first_seen_beyond_fixed_gate():
    detector = SpanPassageDetector()
    for i in range(8):
        detector.update([observation(53 - 5 * i)], i * 0.2)
    assert len(detector.events) == 1
    event = detector.events[0]
    assert event["view_motion"] == "negative_y"
    assert event["gate_y_px"] is None
    assert event["time_semantics"] == "observed_track_midpoint"
    assert 0 < event["crossing_time_s"] < event["confirmed_at_s"]
    assert len(event["observed_track_points"]) >= detector.config.min_observations
    assert all(
        point["time_s"] <= event["confirmed_at_s"] for point in event["observed_track_points"]
    )
    at_confirmation = len(event["continued_track_points"])
    initial_evidence_count = len(event["observed_track_points"])
    detector.update([observation(13)], 1.6)
    assert len(event["continued_track_points"]) > at_confirmation
    assert len(event["observed_track_points"]) == initial_evidence_count


def test_detects_opposite_direction_without_reflection():
    detector = SpanPassageDetector()
    for i in range(8):
        detector.update([observation(61 + 5 * i, colour="yellow")], i * 0.2)
    assert len(detector.events) == 1
    assert detector.events[0]["view_motion"] == "positive_y"


def test_rejects_stationary_and_lateral_motion():
    detector = SpanPassageDetector()
    for i in range(12):
        detector.update([observation(70)], i * 0.2)
    assert detector.events == []
    detector = SpanPassageDetector()
    for i in range(8):
        detector.update([observation(70 - i, x=130 + 5 * i)], i * 0.2)
    assert detector.events == []
