# Estonia S38: choosing the receiving view for post-event state

The 360p [full-match candidate sequence](right-large-cap-full-candidate-pre-post-image-state-handoff-refined-coverage.json) labels the provisional yellow passage at **1759.52 s** as `left:R01-S38` (`P034`), with one earlier right-view time/colour candidate, `R01:A079`. Its post-candidate scan uses the **right** panel at 1774.52, 1779.52 and 1784.52 s and reports `no_stable_colour_cap_proposals`. Source frames show that panel looking toward the next delivery area; the house receiving S38 is in the **left** panel. The right-panel result cannot be interpreted as an empty post-throw board.

The 1080p [S02 cross-view handoff](yellow-s02-cross-view-observation-handoff-postreview-v2.json) has the same colour and passage time, an observed right path through 1758 s, and a left receiving path from 1758.5 to 1771.5 s. The [cross-resolution audit](yellow-s02-cross-resolution-alignment-postreview.json) compares decoded full-match and 1080p frames within ±30 frames at 1759.5 and 1779.5 s; zero offset has the lowest grayscale difference at both checkpoints. This supports joining the selected excerpt evidence to `R01-S38` at those times, without assuming global synchronization elsewhere.

The [left receiving-house source sheet](yellow-s02-left-post-partial-image-caps-postreview.jpg) and [measurement](yellow-s02-left-post-partial-image-caps-postreview.json) show **two yellow cap-like components** at repeated image positions across 1784.5, 1789.5 and 1794.5 s. Their median 1080p left-panel centres are (253, 576) and (710, 777), with maximum centre shifts 1.118 and 0 px, respectively. A third yellow component at 1784.5 s is partly obscured later and is not counted as stable. This is a partial camera-local image observation; it does not identify which cap, if any, belongs to the delivered S38 stone, and it does not measure all stones or a physical settle time.

The reproducible [single-row full-match enrichment](full-match-s38-highres-state-enrichment-postreview.json) preserves `P034`'s original `game_state_after` unknowns and adds the high-resolution right path, cross-view overlap, left path, and partial left board as separately qualified evidence. It records both media hashes and input hashes. **S38 is still a provisional candidate; complete board and simulation readiness remain false/unknown.** The correction is about sampling the receiving view for state, not a new event-F1 or game-state accuracy result.

A subsequent [full-match receiving-view router](../layout-router/full-2024-coverage/RECEIVING-VIEW-BOARD-ROUTING.md) marks S38 and 61 other Estonia candidates for conditional left-panel board sampling. Its 360p S38 scan repeats yellow caps at (84,192) and (236,259), consistent with the two 1080p locations above after resolution scaling. It also repeats a red rink-marking blob; colour and stability alone must not be promoted to stone truth.

The [bounded left-view pre/post comparison](full-match-routed-left-pre-post-cap-deltas-postreview.json) cancels that red marking and one persistent yellow cap. It records a yellow cap near (92,219) as no longer observed and one near (236,259) as newly observed. The physical identities of those caps and the delivered stone remain unknown.

Reproduce the selected post-review checks with:

```sh
feasibility/scripts/python.sh prototype/scripts/audit_estonia_s02_left_post_caps.py
feasibility/scripts/python.sh prototype/scripts/audit_estonia_s02_cross_resolution_alignment.py
feasibility/scripts/python.sh prototype/scripts/export_estonia_s38_full_match_enrichment.py
```
