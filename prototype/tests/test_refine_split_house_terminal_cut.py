from prototype.scripts.refine_split_house_terminal_cut import sustained_tail_start


def row(t, low):
    return {"source_time_s": t,
            "status": "house_paint_unresolved_review" if low
            else "house_paint_aligned_sample"}


def test_sustained_tail_requires_five_consecutive_low_samples():
    assert sustained_tail_start([row(1, False), row(2, True), row(3, True)]) is None
    assert sustained_tail_start([row(1, True), row(2, False),
                                 *[row(t, True) for t in range(3, 8)]]) == 3
