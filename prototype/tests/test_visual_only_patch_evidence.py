from prototype.visual_only_patch_evidence import patch_evidence_status, summarize_tracks


def track(scores):
    return {
        "span_px": 50,
        "points": [{"time_s": index, "patch_score": score} for index, score in enumerate(scores)],
    }


def test_negative_track_is_diagnostic_not_dropped():
    rows = summarize_tracks([("red", track([-2, -1, -3]))], 0)
    assert rows[0]["median_patch_score"] == -2
    assert patch_evidence_status(rows) == "cap_tracks_without_stone_like_patch_support"


def test_positive_median_is_reported():
    rows = summarize_tracks([("yellow", track([-1, 1, 2]))], 0)
    assert rows[0]["median_patch_accepted"]
    assert patch_evidence_status(rows) == "stone_like_patch_track_present"
