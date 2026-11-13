# Lower-ice activity in static-left intervals: exposed development diagnostic

The left-trigger coverage handoff marks 365 s of Italy and 1655 s of Latvia as
detector blind because the left panel stays static while the right panel changes.
That right-panel change can come from athletes rather than delivered stones. To
probe that ambiguity for *review priority*, the [reproducible audit](../../../../prototype/scripts/audit_split_blind_lower_ice_motion.py)
compares grayscale source frames every five seconds in the right-panel lower-ice
image ROI `x=330:630, y=230:325`. It excludes the first and last 20 seconds
of each blind interval from the summary. The ROI and mean-absolute-difference
threshold `>3` were chosen **after looking at these two recordings**, so this
is not a trained or held-out event detector.

| Static-left source interval | Interior five-second pairs | Lower-ice difference median | Pairs above 3 |
| --- | ---: | ---: | ---: |
| [Italy 2835–3200 s](../../canada-italy/left-blind-lower-ice-motion-development.json) | 66 | 0.65244 | **0** |
| [Latvia 5015–6670 s](../../canada-latvia-2024/left-blind-lower-ice-motion-development.json) | 324 | 1.02870 | **50** |

The [Italy right-panel source sheets](../../canada-italy/left-blind-right-view-10s-source-sheets/manifest.json)
sample 36 frames ten seconds apart. They show repeated athlete and wheelchair
movement in front of the house while the lower ice is largely empty/still at
those sampled instants. A [Latvia source review](latvia24-full-v1/right-static-track-review/manifest.json)
already shows moving-stone pixels on several prediction-selected right tracks
in its blind interval. That prior review is not exhaustive or independent.

To inspect what the numerical spikes actually mean, [source strips around all
15 grouped Latvia peaks](../../canada-latvia-2024/left-blind-lower-ice-spike-source-sheets/manifest.json)
show the frame five seconds before, at, and five seconds after each peak. Early
strips overlap visible stone movement, but many later lower-ice changes are
clearly caused by athletes or wheelchairs crossing the foreground. The 50
above-threshold pairs must **not** be used as a proxy stone count or a direct
right-view throw trigger. This source review is by the detector developer and
the three-frame strips do not rule out stones between samples.

The comparison and the earlier eight right-entry review proposals, several
showing short moving-stone paths, keep **Latvia as a right-view recall-recovery
target**; Italy's sampled static-left interval
may be a lull or repositioning period. They do *not* prove Italy had zero
throws, that Latvia had 50 throws, or that either interval's physical
deliveries have been counted.
Five-second samples can miss a short transit, lower-ice motion has several
possible causes, and source-first exhaustive throw labels are still required
for precision/recall/F1. The candidate timelines and game-state fields remain
unchanged.
