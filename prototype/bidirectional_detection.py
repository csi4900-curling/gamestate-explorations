"""Exploratory opposite-direction passages using the unchanged baseline tracker.

The incoming view is reflected about the existing y=60 gate before tracking.
This keeps all baseline size, speed, span and association conditions identical.
Both directions are retained as candidates; a later phase model must select
which direction is a throw in a given camera/end state.
"""

from throw_detection import PassageDetector, PassageConfig


def crossing_x(event, points):
    """Interpolate image x at the observed gate time; never infer a release point."""
    crossing = event["crossing_time_s"]
    for before, after in zip(points, points[1:]):
        a, b = before["time_s"], after["time_s"]
        if a <= crossing <= b and b > a:
            fraction = (crossing - a) / (b - a)
            return before["pixel"][0] + fraction * (after["pixel"][0] - before["pixel"][0])
    raise ValueError(f"No crossing observations for {event['id']}")


class IncomingPassageDetector:
    def __init__(self, config=None):
        self.config = config or PassageConfig()
        self.inner = PassageDetector(self.config)

    def update(self, candidates, t):
        reflected = []
        for candidate in candidates:
            transformed = dict(candidate)
            x, y, w, h = candidate["bbox"]
            transformed["bbox"] = [x, 2 * self.config.gate_y - y - h, w, h]
            transformed["pixel"] = [
                candidate["pixel"][0],
                2 * self.config.gate_y - candidate["pixel"][1],
            ]
            reflected.append(transformed)
        return [self._restore(e) for e in self.inner.update(reflected, t)]

    def _restore(self, event):
        restored = dict(event)
        track = next(
            track
            for track in self.inner.finished + self.inner.tracks
            if track.id == event["track_id"]
        )
        restored["id"] = f"I{event['id'][1:]}"
        restored["crossing_x_px"] = crossing_x(event, track.points)
        restored["velocity_px_s"] = [event["velocity_px_s"][0], -event["velocity_px_s"][1]]
        restored["view_motion"] = "positive_y"
        return restored

    @property
    def events(self):
        return [self._restore(e) for e in self.inner.events]
