"""Right-panel probe should not ingest coloured graphics in the left panel."""

import cv2
import numpy as np

from scripts.probe_static_left_right_cap_motion import right_colour_proposals
from scripts.render_right_static_track_review import selected


def test_small_colour_blobs_only_inside_right_rink_roi():
    frame = np.full((360, 640, 3), 220, dtype=np.uint8)
    cv2.rectangle(frame, (400, 250), (410, 257), (0, 0, 255), -1)
    cv2.rectangle(frame, (500, 250), (510, 257), (0, 255, 255), -1)
    cv2.rectangle(frame, (100, 250), (110, 257), (0, 0, 255), -1)
    proposals = right_colour_proposals(frame)
    assert len(proposals["red"]) == 1
    assert len(proposals["yellow"]) == 1
    assert proposals["red"][0]["pixel"] == [405.5, 254.0]


def test_review_rule_is_upward_motion_not_generic_track():
    def track(first, last, duration):
        return {"points": [{"pixel": first}, {"pixel": last}],
                "first_observed_s": 0, "last_observed_s": duration}
    assert selected(track([500, 300], [510, 190], 12))
    assert not selected(track([500, 300], [510, 190], 90))
    assert not selected(track([500, 150], [510, 100], 12))
    assert not selected(track([500, 300], [510, 350], 12))
