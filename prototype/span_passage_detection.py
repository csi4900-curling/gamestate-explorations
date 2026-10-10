"""Line-independent motion-span candidates in the fixed 2024 left-panel ROI.

The baseline colour/body proposal and tracker are reused unchanged. A candidate
is emitted after a tracked object moves far enough through the early ice ROI,
even if its first observation is already beyond a chosen virtual line.
"""

import numpy as np

from throw_detection import PassageConfig, PassageDetector


class SpanPassageDetector:
    def __init__(self, config=None):
        self.config = config or PassageConfig()
        self.tracker = PassageDetector(self.config)
        self.events = []
        self._seen_tracks = set()
        self._event_by_track = {}

    def update(self, candidates, t):
        self.tracker.update(candidates, t)
        for track in self.tracker.tracks:
            event = self._event_by_track.get(track.id)
            if event and track.points[-1]["time_s"] > event["continued_track_points"][-1]["time_s"]:
                event["continued_track_points"].append(dict(track.points[-1]))
        new = []
        for track in self.tracker.tracks:
            if track.id in self._seen_tracks:
                continue
            recent = [point for point in track.points if t - point["time_s"] <= 4]
            if len(recent) < self.config.min_observations:
                continue
            xy = np.asarray([point["pixel"] for point in recent], dtype=float)
            times = np.asarray([point["time_s"] for point in recent], dtype=float)
            dy = xy[-1, 1] - xy[0, 1]
            if abs(dy) < self.config.min_span_px:
                continue
            vx, vy = np.polyfit(times - times[0], xy, 1)[0]
            if not self.config.min_speed_px_s < abs(vy) < self.config.max_speed_px_s:
                continue
            if abs(vx) > abs(vy) * 0.8 or np.sign(vy) != np.sign(dy):
                continue
            direction = "positive_y" if dy > 0 else "negative_y"
            monotonic = float(np.mean(np.diff(xy[:, 1]) * np.sign(dy) > -1))
            if monotonic < 0.85:
                continue
            # The midpoint is an observed passage timestamp, never an inferred
            # release time. It lies between two actual tracked observations.
            midpoint_y = (xy[0, 1] + xy[-1, 1]) / 2
            timestamp, crossing_x = None, None
            for before, after in zip(recent, recent[1:]):
                y0, y1 = before["pixel"][1], after["pixel"][1]
                if (midpoint_y - y0) * (midpoint_y - y1) > 0 or y0 == y1:
                    continue
                alpha = (midpoint_y - y0) / (y1 - y0)
                timestamp = before["time_s"] + alpha * (after["time_s"] - before["time_s"])
                crossing_x = before["pixel"][0] + alpha * (after["pixel"][0] - before["pixel"][0])
                break
            if timestamp is None:
                continue
            self._seen_tracks.add(track.id)
            if any(
                event["colour"] == track.colour
                and event["view_motion"] == direction
                and abs(event["crossing_time_s"] - timestamp) < 1.5
                and abs(event["crossing_x_px"] - crossing_x) < 15
                for event in self.events
            ):
                continue
            event = {
                "id": f"S{len(self.events) + 1:02}",
                "track_id": track.id,
                "colour": track.colour,
                "crossing_time_s": round(float(timestamp), 3),
                "time_semantics": "observed_track_midpoint",
                "confirmed_at_s": round(float(t), 3),
                "first_observed_s": track.points[0]["time_s"],
                "evidence_kind": "early_roi_motion_span",
                "release_time_s": None,
                "gate_y_px": None,
                "crossing_x_px": float(crossing_x),
                "passage_y_px": float(midpoint_y),
                "velocity_px_s": [float(vx), float(vy)],
                "observations_at_confirmation": len(recent),
                "observed_span_px": float(abs(dy)),
                "median_candidate_bbox_width_px": float(np.median([p["bbox"][2] for p in recent])),
                "median_candidate_bbox_height_px": float(np.median([p["bbox"][3] for p in recent])),
                "mean_body_support": float(np.mean([p["body_support"] for p in recent])),
                "recent_track_duration_s": float(times[-1] - times[0]),
                "direction_consistency": monotonic,
                "view_motion": direction,
                "observed_track_points": [dict(point) for point in recent],
                "continued_track_points": [dict(point) for point in track.points],
            }
            self.events.append(event)
            self._event_by_track[track.id] = event
            new.append(event)
        return new
