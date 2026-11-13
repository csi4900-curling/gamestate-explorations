# Direction-aware yellow motion with a full right-panel contour search

The [post-review transfer result](yellow-full-right-panel-contour-transfer-postreview-v2.json) keeps the previously preserved sustained-motion episodes in both image directions. It changes one image-processing limit: yellow handle contours may now be selected across the right-panel ice region from image y=0 through y=1080, rather than stopping at y=970. The body-to-contour association and visual-stillness rule remain unchanged. For each scanned frame, the runner checks that contours within the old region are byte-for-byte equal to the frozen contour implementation's output.

| Selected recording | Direction | Last linked right-view sample | Visual-stillness bracket | Interpretation |
| --- | --- | ---: | --- | --- |
| Canada–Korea T11 | upward | 2320 s | 2317–2318 s | Same candidate stop bracket as earlier probe |
| Canada–Slovakia | upward | 2051 s | 2048–2049 s | Same candidate stop bracket as earlier probe |
| Canada–Estonia S02 window | downward | **1758 s**, image centre (1384.5, 1026) | none | Stone reaches near-bottom panel boundary; right-view path is censored |

The Estonia 1758 s contour was visible in the source but excluded by the old y≤970 region. Its newly linked step from 1757 s is 81.56 px, with one contour inside the motion gate. The stone subsequently exits the right panel; the result does **not** infer a stop there. The revised [S02 observation handoff](../../canada-estonia-2024/yellow-s02-cross-view-observation-handoff-postreview-v2.json) carries this sixth right-view sample and the separately measured left-view bridge.

This is an exposed, selected three-window development check. It demonstrates that the specific near-boundary failure can be repaired without changing Korea and Slovakia outputs. It does not establish general contour precision, throw-event recall, cross-view physical identity, settled boards, or full-match F1. The first frozen Estonia outcome and the first post-review transfer remain preserved separately.

Reproduce with `feasibility/scripts/python.sh prototype/scripts/transfer_bidirectional_full_right_contours.py` after moving the versioned output aside.
