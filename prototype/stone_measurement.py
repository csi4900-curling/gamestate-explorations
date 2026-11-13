"""Decide whether an observed body box identifies its full image centre.

Clipping a box to a frame or split-panel boundary changes its midpoint. Keep
the detector observation for tracking, but do not project that censored midpoint
as a measured stone centre. No position is extrapolated from the hidden body.
"""


def body_point_support(detection, source_size):
    width, height = source_size
    x0, y0, x1, y1 = detection['bbox_xyxy']
    boundaries = []
    if x0 <= 0:
        boundaries.append('source_left')
    if y0 <= 0:
        boundaries.append('source_top')
    if x1 >= width:
        boundaries.append('source_right')
    if y1 >= height:
        boundaries.append('source_bottom')
    if x0 <= width / 2 <= x1:
        boundaries.append('split_panel_boundary')
    return {'status': 'censored_body_box' if boundaries else 'full_body_box',
            'centre_supported': not boundaries, 'censored_boundaries': boundaries,
            'point_semantics': 'Detected box midpoint; a censored box does not identify the full stone centre'}
