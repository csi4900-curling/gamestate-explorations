# Object-overhead check on frozen accepted paths (development)

The learned one-of-three cap-patch screen accepted two source-reviewed non-stone paths: S96 follows a wheelchair footrest during play, and S143 follows a wheelchair during postgame exit. A stone-like coloured crop alone was therefore insufficient. The [reproducible audit](../../../prototype/scripts/audit_path_overhead_darkness.py) measures how much of the central column **15–100 pixels above each patch-positive cap box** is dark (HSV value < 100) in the 1080p source. A proposed development abstention requires **every** patch-positive sample to have a dark fraction ≥ 0.75. Missing measurements do not trigger it. The geometry and threshold were chosen after viewing S96 and S143; they are not independently learned or validated.

**Association correction (later audit):** These measurements belong to
downstream paths associated with candidate IDs, not to verified continuations
of the original early-ROI trigger tracks. For S96, the
[direct anchor audit](../layout-router/czech24-full-camera-motion-v1/raw-to-downstream-left-anchor-audit.json)
finds that
the raw 4037.6 s centre and downstream 4037.5 s centre are 183.032 px apart
at 1080p scale. Thus the S96 overhead result cannot be claimed as a filter
of the raw triggering object. The downstream path itself remains
source-reviewed as a footrest; S143 raw-to-downstream identity is also
unverified. No frozen screen output was changed.

| Source | Frozen accepted paths measured | Incomplete measurements | Proposed new abstentions |
| --- | ---: | ---: | --- |
| [Canada–Czechia full match](overhead-darkness-development-postscore.json) | 79 | 0 | S96, S143 |
| [Canada–Slovakia 1650–2760 s](../../curlobserver-learned-probe/canada-slovakia-2024-overhead-darkness-development-postscore.json) | 17 | 0 | none |
| [Canada–Italy 1650–2760 s](../../curlobserver-learned-probe/canada-italy-2024-overhead-darkness-development-postscore.json) | 14 | 0 | none |
| [Canada–Estonia 1650–2760 s](../../curlobserver-learned-probe/canada-estonia-2024-overhead-darkness-development-postscore.json) | 17 | 0 | none |
| [Canada–Latvia 1650–2760 s](../../curlobserver-learned-probe/canada-latvia-2024-overhead-darkness-development-postscore.json) | 15 | 0 | none |
| [Canada–Scotland 1650–2760 s](../../curlobserver-learned-probe/canada-scotland-2024-overhead-darkness-development-postscore.json) | 17 | 0 | none |
| **Total** | **159** | **0** | **2** |

S96's lowest patch-positive overhead dark fraction is **0.911** and S143's is **0.931**. The highest candidate minimum among all 157 other accepted paths is **0.068** (Scotland S01). Source crops show why: the wheelchair footrests have a dark chair and occupant directly above, whereas source-visible stone controls S07, S21, S42 and S69 are isolated in the measurement column when their learned patches pass. This is a much larger exposed-set separation than the neutral-gray body-band check, which caught only S96. The six JSON artifacts record every positive-patch sample, cap box, decoded frame index, source and code hash. The frozen screen and its 79 Czechia acceptances remain unchanged.

**Limits.** This is a selected hard-negative check, not precision, recall, or F1: only two false paths were source-reviewed, the other 157 acceptances are not independently verified, and missed throws never enter the audit. An actual stone travelling directly beneath a player, camera graphic, or other dark object could be wrongly abstained. The feature is 1080p- and layout-dependent; it needs an independently labelled set with near-player true throws and false positives from other views before it can be a production rejection rule. It measures visual isolation at a few samples, not persistent stone identity along the full path.
