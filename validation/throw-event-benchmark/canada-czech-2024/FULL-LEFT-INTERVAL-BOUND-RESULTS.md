# Extended left proposal bound: complete corridor intervals

The [S41 source diagnostic](LEFT-BOUND-RECALL-DIAGNOSTIC.md) suggested that
the left receiving view's −6.401 m proposal limit can censor a visible stone.
We replayed every positive-y **corridor candidate** in five separate 2024
recording intervals (1650–2760 s) with both the original limit and −18 m.
The [batch runner](../../../prototype/scripts/run_left_world_bound_batch.py)
holds registration, 0.5 s sampling, stone proposal logic, and path selection
fixed. Each candidate result is stored separately and checked against the
source, candidate, calibration, detector, selector, and runner hashes.

| Recording | Left corridor candidates | Original unique / ambiguous / unsupported | Extended unique / ambiguous / unsupported | Changed selection IDs |
| --- | ---: | ---: | ---: | --- |
| [Canada–Slovakia](../canada-slovakia-2024/left-bound-full-interval/manifest.json) | 7 | 4 / 1 / 2 | 4 / 1 / 2 | none |
| [Canada–Italy](../canada-italy/left-bound-full-interval/manifest.json) | 6 | 1 / 0 / 5 | 2 / 0 / 4 | S03 |
| [Canada–Estonia](../canada-estonia-2024/left-bound-full-interval/manifest.json) | 7 | 4 / 0 / 3 | 4 / 0 / 3 | none |
| [Canada–Latvia](../canada-latvia-2024/left-bound-full-interval/manifest.json) | 7 | 4 / 0 / 3 | 4 / 0 / 3 | none |
| [Canada–Scotland](../canada-scotland-2024/left-bound-full-interval/manifest.json) | 5 | 2 / 0 / 3 | 3 / 0 / 2 | S02 |
| **Total** | **32** | **15 / 1 / 16** | **17 / 1 / 14** | **2 IDs** |

The Slovakia original-bound statuses match its existing post-rescue motion
audit for all seven left candidates. More distant proposals lengthen selected
paths there, but no candidate changes category. Neither unsupported Slovakia
candidate becomes a unique path.

Italy S03 is the other changed case. The [marked source frames](../canada-italy/left-bound-full-interval/s03-source-review/s03-path-review.jpg)
show a yellow stone at 1793.5, 1796.5, and 1799.0 s. The extended-bound
selector keeps 12 consecutive observations; its direct original-bound replay
keeps no unique path. The existing [frozen repair screen](../../curlobserver-learned-probe/canada-italy-2024-candidate-motion-patch-screen-frozen-repair-transfer.json)
abstained on S03, while a separate [later development screen](../../curlobserver-learned-probe/canada-italy-2024-candidate-dropout-rescue-screen-development.json)
already provisionally accepted a five-sample shared prefix with one of three
positive appearance patches. The wider-bound result is a stronger *motion
proposal* on this exposed clip; it has not yet passed the frozen appearance
screen as a new event, and independent throw truth is absent.

Scotland S02 is a source-visible yellow stone. The [marked source frames](../canada-scotland-2024/left-bound-full-interval/s02-source-review/s02-path-review.jpg)
show the extended-bound path following it at 1743.5, 1745.5, and 1747.5 s.
The direct original-bound replay had no selected path in that early window;
the extended-bound replay selects nine observations from 1743.5–1747.5 s.
**This is not a newly recovered throw in the existing later-stage screen:**
the [Scotland dropout screen](../../curlobserver-learned-probe/canada-scotland-2024-dropout-screen-frozen-first.json)
already provisionally accepted S02 using a seven-observation later path from
1747.5–1750.5 s (two of three appearance patches positive). The early path
and existing later path have an identical observed stone center at 1747.5 s.
A [checked same-view join](../canada-scotland-2024/left-bound-full-interval/s02-joined-conditional-path.json)
therefore preserves 15 consecutive 0.5 s observations from 1743.5–1750.5 s.
The join is a **conditional trajectory observation**, not verified physical
identity, release/settle timing, metric accuracy, spin, or simulation input.

The evidence supports extended proposal coverage for S41, a longer early
stone track for Scotland S02, and a unique stone-like path for Italy S03.
These are **motion-selector changes**, not measured event-level recall gains.
An [isolated frozen-model appearance check](LEFT-BOUND-PATCH-RESULTS.md)
provisionally supports all three stone paths, but also continues to support
the known S143 postgame false path.
The screen already accepted Scotland S02, and Italy S03's downstream outcome
depends on which development version is used. The two known Canada–Czechia
false-positive paths persist under the wider bound. The scan covers only
corridor candidates in 18.5-minute intervals, not all possible throws or
other camera views. The frozen candidate screens remain unchanged;
independent exhaustive throw labels and full-recording checks are still
required for precision, recall, and F1.
