"""Beijing 2022 broadcast stone-counter adapter and evidence state machine.

This adapter applies only to the verified 640x360 overlay layout. An absent or
unreadable graphic yields unknown rather than a guessed count. Count changes
give delivery evidence, not an observed release or physical stone trajectory.
"""

from dataclasses import dataclass

import cv2


SLOT_X = tuple(range(149, 282, 18))


def read_beijing_counts(frame):
    """Return remaining red/yellow stones or None if the overlay is unsupported."""
    if frame is None or frame.ndim != 3 or frame.shape[2] != 3:
        raise ValueError("Expected a BGR frame")
    image = cv2.resize(frame, (640, 360), interpolation=cv2.INTER_AREA)
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    background = hsv[16:54, 138:289]
    flag_panel = hsv[16:54, 65:135]
    dark_blue = (
        (background[:, :, 0] > 90)
        & (background[:, :, 0] < 135)
        & (background[:, :, 1] > 60)
        & (background[:, :, 2] < 180)
    )
    pale = (flag_panel[:, :, 1] < 80) & (flag_panel[:, :, 2] > 160)
    if dark_blue.mean() < 0.20 or pale.mean() < 0.50:
        return None
    counts = []
    for colour, y in (("red", 26), ("yellow", 44)):
        slots = []
        for x in SLOT_X:
            patch = hsv[y - 5 : y + 6, x - 5 : x + 6]
            hue, saturation, value = cv2.split(patch)
            if colour == "red":
                mask = ((hue < 12) | (hue > 170)) & (saturation > 85) & (value > 60)
            else:
                mask = (hue > 16) & (hue < 43) & (saturation > 85) & (value > 60)
            slots.append(int(mask.sum()) >= 20)
        count = sum(slots)
        if slots != [True] * count + [False] * (8 - count):
            return None
        counts.append(count)
    return tuple(counts)


@dataclass
class CountState:
    counts: tuple[int, int]
    first_seen_s: float
    last_seen_s: float


class ScoreboardEvents:
    """Emit one event per stable one-stone decrement; retain unresolved gaps."""

    def __init__(self, stable_samples=3, max_gap_s=35.0):
        self.stable_samples = stable_samples
        self.max_gap_s = max_gap_s
        self.pending_counts = None
        self.pending_first_s = None
        self.pending_samples = 0
        self.state = None
        self.events = []
        self.unresolved = []
        self.observations = 0
        self.visible_samples = 0
        self.reset_grace_until_s = float("-inf")
        self.reset_candidate = None
        self.rejected_rise_counts = None

    def update(self, counts, t):
        self.observations += 1
        if counts is None:
            self.pending_counts = None
            self.pending_samples = 0
            return []
        self.visible_samples += 1
        if len(counts) != 2 or any(not isinstance(c, int) or not 0 <= c <= 8 for c in counts):
            raise ValueError("Invalid stone count")
        if self.state is not None:
            rises = tuple(after - before for before, after in zip(self.state.counts, counts))
            if all(delta >= 2 for delta in rises):
                if self.reset_candidate is None or t - self.reset_candidate["first_s"] > 15:
                    self.reset_candidate = {
                        "first_s": t,
                        "counts": counts,
                    }
                    self.pending_counts = None
                    self.pending_samples = 0
                    return []
                candidate = self.reset_candidate
                candidate["counts"] = tuple(max(a, b) for a, b in zip(candidate["counts"], counts))
                self.unresolved.append(
                    {
                        "kind": "counter_reset_or_inconsistent",
                        "time_interval_s": [self.state.last_seen_s, candidate["first_s"]],
                        "before": self.state.counts,
                        "after": candidate["counts"],
                    }
                )
                self.state = CountState(candidate["counts"], candidate["first_s"], t)
                self.reset_grace_until_s = t + 25
                self.reset_candidate = None
                self.rejected_rise_counts = None
                self.pending_counts = None
                self.pending_samples = 0
                return []
            self.reset_candidate = None
            if any(delta > 0 for delta in rises) and t <= self.reset_grace_until_s:
                self.state.counts = tuple(max(a, b) for a, b in zip(self.state.counts, counts))
                self.state.last_seen_s = t
                self.pending_counts = None
                self.pending_samples = 0
                return []
        if self.pending_counts != counts:
            self.pending_counts = counts
            self.pending_first_s = t
            self.pending_samples = 1
        else:
            self.pending_samples += 1
        if self.pending_samples < self.stable_samples:
            return []
        if self.state is None:
            self.state = CountState(counts, self.pending_first_s, t)
            return []
        if self.state.counts == counts:
            self.state.last_seen_s = t
            self.rejected_rise_counts = None
            return []
        previous = self.state
        change = tuple(before - after for before, after in zip(previous.counts, counts))
        gap_s = self.pending_first_s - previous.last_seen_s
        if any(delta < 0 for delta in change):
            # A one-row upward misread can last several seconds. Promoting it
            # makes its later return look like a delivered stone. Keep the
            # last monotone state and record the uncertainty only once.
            if self.rejected_rise_counts != counts:
                self.unresolved.append(
                    {
                        "kind": "counter_reset_or_inconsistent",
                        "time_interval_s": [previous.last_seen_s, t],
                        "before": previous.counts,
                        "after": counts,
                    }
                )
                self.rejected_rise_counts = counts
            return []
        self.state = CountState(counts, self.pending_first_s, t)
        self.rejected_rise_counts = None
        if sum(change) == 1 and gap_s <= self.max_gap_s:
            colour = "red" if change[0] else "yellow"
            event = {
                "id": f"B{len(self.events) + 1:02}",
                "colour": colour,
                "crossing_time_s": self.pending_first_s,
                "evidence_interval_s": [previous.last_seen_s, self.pending_first_s],
                "evidence_kind": "broadcast_remaining_stone_counter_decrement",
                "release_time_s": None,
                "confirmed_at_s": t,
                "remaining_before": previous.counts,
                "remaining_after": counts,
            }
            self.events.append(event)
            # The reset grace may absorb an initial slot blink until the first
            # decrement is confirmed. Keeping it active afterward lets a
            # later one-frame rise restore the count and emits the same
            # decrement again when the blinking slot settles a second time.
            self.reset_grace_until_s = float("-inf")
            return [event]
        self.unresolved.append(
            {
                "kind": "multi_throw_or_long_graphic_gap",
                "time_interval_s": [previous.last_seen_s, t],
                "before": previous.counts,
                "after": counts,
            }
        )
        return []
