# First fixed yellow-contour transfer: direction failure on Estonia

The [predeclared 1720–1800 s window](YELLOW-CONTOUR-TRANSFER-PLAN.md) was
scanned using the Korea/Slovakia body template, raw yellow handle contours,
motion association and visual-stillness rule without changing parameters.
The [first-result artifact](yellow-contour-1720-1800-first-transfer.json)
contains **121 body proposals**, **33 yellow-handle-supported boxes** and
**40 yellow contours** in the right-ice region. It produces **one linked
body path at 1731–1757 s**, but that path is marked **downward** (+364 px in
1080p image y). The frozen *upward-only* seed gate consequently returns
**zero contour handoffs** and no visual stop.

The [eight-frame source sheet](yellow-contour-1720-1800-first-source-review.jpg)
and [same-agent review record](yellow-contour-1720-1800-first-source-review.json)
show a yellow stone moving toward the camera at 1753–1758 s. The linked
body boxes follow it at 1753–1757 s, with successive steps of roughly
73, 77, 82 and 88 px/s. At 1758 s the stone remains visible but the body
template no longer matches; its yellow contour centre plus the fixed body
proxy is at image y ≈1028, outside the frozen contour search limit y ≤970.
The stone exits the right panel by 1759 s while the two-panel broadcast
continues. Thus the right view cannot support a visual-stop
claim even with a direction-aware handoff.

The earlier portion of the same linked path, 1731–1752 s, sits near image
y≈581–615 with little movement. Source inspection does **not** verify that
this early object is physically the same stone. The path linker may have
joined a nearly stationary object to the later delivery. Consequently the
first matched time, 1731 s, is not a defensible throw-start timestamp.

This first transfer exposes three concrete limits: the detector assumes
delivery always moves upward in the right image, its ROI excludes a near
camera stone, and its current linker can attach long stationary prefixes to
moving stone episodes. The result was selected using a provisional yellow
left-view candidate, and source classes were reviewed by the developer; it
is not independent event validation. The correct next representation needs
view-specific delivery direction, a motion-onset split, and explicit
right-censoring at image boundaries and camera changes. Physical identity,
metric trajectory, board state and simulation remain unverified.

Reproduce with:

```sh
feasibility/scripts/python.sh prototype/scripts/transfer_yellow_contour_estonia.py
feasibility/scripts/python.sh prototype/scripts/render_estonia_yellow_first_transfer.py
```

A later [postscore motion-episode interpretation](../layout-router/full-2024-coverage/BIDIRECTIONAL-YELLOW-MOTION-EPISODES.md)
separates the 22 nearly stationary early matches from sustained downward
motion beginning in the **1753–1754 s observation bracket**. It preserves
the original failed first pass and marks the episode right-censored; it does
not infer physical release or same-stone identity.

A separate [post-review two-camera bridge](YELLOW-S02-CROSS-VIEW-BRIDGE.md)
shows simultaneous yellow edge visibility and tracks the left-entry contour
into the earlier S02 left path. That follow-up strengthens the provisional
handoff; it does not change the frozen first-pass outcome or supply an
independent event metric.
