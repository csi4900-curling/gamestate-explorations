# S96 raw trigger: source-pixel review

The [manifest](manifest.json) pins three unmarked 640×360 source frames,
decoded frame indices, source/code hashes, and the raw S96 pixel positions.
The track point is at (100.0, 82.0) at
[4036.8 s](source-4036.8.png), (100.5, 102.5) at
[4037.6 s](source-4037.6.png), and (100.5, 116.0) at
[4038.2 s](source-4038.2.png). In those frames, the coloured feature moves
down with the viewer-right edge of the upper Canadian player's wheelchair /
body, rather than as an isolated stone on the ice. This is an **agent
source-pixel review**, not an independent label or an exhaustive event audit.

The older [S96 source review](../../../canada-czech-2024/source-review/s96-review.json)
also found a wheelchair footrest, but its selected downstream path is a
different spatial track: at nearly the same time, its centre is
[183.032 px away](../raw-to-downstream-left-anchor-audit.json) in 1080p
coordinates. These two observations support a non-stone failure mode at S96,
while also showing that a later appearance score cannot be attributed to
the raw trigger without a verified handoff.
