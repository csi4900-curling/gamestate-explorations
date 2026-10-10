"""The fixed-grid selector must keep distinct camera poses apart."""

from prototype.scripts.select_camera_reference_anchor import (
    cluster_registered,
    select_anchor,
)


def row(t, x, inliers=20, rmse=0.5):
    return {
        "source_time_s": t,
        "status": "registered",
        "inliers": inliers,
        "rmse_px": rmse,
        "current_corners_px": [[x, 0], [x + 10, 0], [x + 10, 10], [x, 10]],
    }


def test_distinct_poses_do_not_chain_through_an_intermediate_frame():
    clusters = cluster_registered([row(0, 0), row(1, 30), row(2, 60)], 40)
    assert [[member["source_time_s"] for member in group] for group in clusters] == [[0, 1], [2]]


def test_choose_dominant_pose_then_best_feature_support():
    clusters = cluster_registered([row(0, 0), row(1, 5, 24), row(2, 100, 90)], 40)
    chosen, anchor = select_anchor(clusters)
    assert len(chosen) == 2
    assert anchor["source_time_s"] == 1
