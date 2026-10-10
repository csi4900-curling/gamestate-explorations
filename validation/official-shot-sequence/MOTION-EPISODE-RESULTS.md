# Stationary-to-motion episode diagnostic

The [China catalog review](CHINA-CATALOG-REVIEW.md) found R01-S211's raw cap
track merged a stationary person/wheelchair component into a moving red
stone. The saved event's `first_observed_s` (6870.0) therefore predates the
stone's visible motion by several seconds. The
[episode rule](../../prototype/motion_episode.py) finds a stable position
prefix followed by at least 15 px of directed travel at at least 8 px/s.
It returns an **observed motion onset**, not an exact release or proof of
physical-object identity.

On [36 previously reviewed tracks](motion-episode-audit-v1.json), it flags
only R01-S211. Its onset is 6876.1 s, followed by 32.5 px of directed motion
at a mean 36.1 px/s through 6877.0 s. The earlier 6874.6–6876.0 s prefix
remains within 3 px horizontally and 3.5 px vertically. The observed
crossing is 6876.522 s. This replaces a misleading six-second track
prehistory with a source-supported moving segment for this event, while
retaining the original frozen event and its uncertainty.

The same fixed rule was then applied to all **368 provisional events** in
the three 2024 full timelines: [China 131](motion-episode-china-all-v1.json),
[Estonia 128](motion-episode-estonia-all-v1.json), and
[Italy 109](motion-episode-italy-all-v1.json). It flags R01-S211 alone.
This is a post-review development audit on exposed sources, not a sensitivity
or precision estimate for identity switches; undetected switches can remain.
It does not reject brooms or players, settle whether an event is a throw,
repair coverage gaps, or produce full-video F1.

The [crossing-local patch comparison](IDENTITY-PATCH-TRANSFER.md) confirms
that this timing correction alone cannot safely classify objects. A model
trained on crossing-local China patches still missed three of seven reviewed
real Estonia stones; its repeated Italy check kept 11 of 17 coarse-window
matched tracks. Even the [R01-S211 stone crops](identity-crossing-patches-s211-v1/Y_U6gzqORUs-contact.jpg)
received a negative [frozen appearance score](s211-crossing-identity-score.json).
The episode is useful as a time-bounded trajectory hypothesis, not as a
hard throw gate.
