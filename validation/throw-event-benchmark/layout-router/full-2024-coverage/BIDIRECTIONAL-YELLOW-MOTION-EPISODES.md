# Yellow-stone image motion across both delivery directions

The [postscore episode ledger](yellow-bidirectional-motion-episodes-postscore.json)
interprets the preserved Korea, Slovakia and Estonia body paths with a
direction-agnostic one-second motion rule. Two consecutive steps of at least
20 px in the same image-y direction, spanning at least 75 px, mark a
*sustained image-motion episode*. The first step brackets an observed onset;
it is not a measured release time. The right-view contour continuation runs
from that episode rather than from any earlier nearly stationary prefix.

| Recording | Sustained image motion | Onset observation bracket | Earlier linked observations | Last linked image point | Visual-stillness bracket |
| --- | --- | --- | ---: | ---: | --- |
| Canada–Korea T11 | upward | 2308–2309 s | 0 | 2320 s | 2317–2318 s |
| Canada–Slovakia | upward | 2034–2035 s | 0 | 2051 s | 2048–2049 s |
| Canada–Estonia S02 window | downward | 1753–1754 s | **22** | 1757 s | unavailable |

For Estonia, the first body match was 1731 s, but the source-reviewed stone
only moves rapidly toward the camera at 1753–1758 s. The 22 earlier linked
observations cannot be treated as the start of that throw; even their
same-stone identity is uncertain. The preserved first pass [rejected the
downward path](../../canada-estonia-2024/YELLOW-CONTOUR-FIRST-TRANSFER-RESULTS.md)
because its seed gate accepted upward motion only. This postresult repair
recovers an image-motion episode but **not** a complete track: the yellow
contour is beyond the original y≤970 search area by 1758 s, and the stone
exits the right panel by 1759 s. The two-panel broadcast continues. The
right-view state is censored, with no visual or physical stop in that view.

The provisional yellow left-view candidate S02 crosses its line at 1759.52 s,
2.52 s after the last right-body observation. A later
[post-review source bridge](../../canada-estonia-2024/YELLOW-S02-CROSS-VIEW-BRIDGE.md)
finds 23 simultaneous right-exit/left-entry yellow frames and follows the
left-entry stone into the prior S02 path, with 1.981 px mean centre difference
over 11 overlapping samples. This substantially strengthens the cross-view
link, but the regions were selected after inspection and physical identity
has not been independently verified. A general link still needs an
orientation-aware delivery model and calibration appropriate to each view.

A later [expanded right-panel contour transfer](YELLOW-FULL-RIGHT-CONTOUR-TRANSFER.md)
adds the source-visible Estonia 1758 s sample beyond the first scan's y≤970
limit. It keeps the Korea and Slovakia candidate-stop brackets unchanged, and
keeps Estonia right-censored rather than inventing a stop.

All three clips and the episode rule were exposed while developing this
diagnostic; it is **not an independent F1 test**. Its value is to prevent a
stationary prefix from masquerading as a throw start and to preserve the
observed travel direction and censoring status. No complete game state,
metric trajectory, spin or simulation output follows from it.

Reproduce with:

```sh
feasibility/scripts/python.sh -m pytest -q prototype/tests/test_sampled_motion_episode.py
feasibility/scripts/python.sh prototype/scripts/derive_yellow_bidirectional_episodes.py
```
