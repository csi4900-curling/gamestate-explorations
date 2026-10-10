"""Sample candidate post-delivery views without crossing the next candidate."""


def post_window_sample_times(window, next_start_s, *, lead_s=4.0, step_s=2.0,
                             horizon_s=32.0, next_margin_s=2.0):
    start_s, end_s = window
    if not start_s < end_s or next_start_s <= start_s:
        raise ValueError("Candidate timing is invalid")
    if lead_s <= 0 or step_s <= 0 or horizon_s <= lead_s or next_margin_s < 0:
        raise ValueError("Sampling parameters are invalid")
    stop_s = min(end_s + horizon_s, next_start_s - next_margin_s)
    times = []
    t = end_s + lead_s
    while t < stop_s:
        times.append(round(t, 3))
        t += step_s
    return times
