"""The diagnostic replay must exactly match the frozen transit summaries."""

import random

from short_cap_transit import short_transits
from short_transit_replay import short_transits_with_points


def test_replay_matches_frozen_transit_summaries_over_varied_tracks():
    rng = random.Random(8341)
    for _ in range(100):
        observations = []
        centers = [[rng.uniform(100, 500), rng.uniform(190, 330)]
                   for _ in range(rng.randint(1, 4))]
        for index in range(rng.randint(5, 45)):
            candidates = []
            for center in centers:
                center[0] += rng.uniform(-25, 25)
                center[1] += rng.uniform(-12, 12)
                if rng.random() < 0.8:
                    candidates.append({"pixel": [round(center[0], 2),
                                                  round(center[1], 2)],
                                       "patch_score": round(rng.uniform(-0.6, 1), 3)})
            rng.shuffle(candidates)
            observations.append((round(index * 0.2, 3), candidates))
        replay = short_transits_with_points(observations)
        assert [summary for summary, _ in replay] == short_transits(observations)
        for summary, points in replay:
            assert len(points) == summary["point_count"]
            assert [points[0]["time_s"], points[-1]["time_s"]] == summary["interval_s"]
            assert points[0]["pixel"] == summary["first_pixel"]
            assert points[-1]["pixel"] == summary["last_pixel"]
