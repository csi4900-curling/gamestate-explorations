# Development stone-body support check

The frozen one-of-three appearance screen accepted 79 full-match candidates,
including source-reviewed false-positive paths S96 (wheelchair footrest) and
S143 (postgame wheelchair movement). Requiring two accepted learned patches
would wrongly remove source-visible stones S07, S21 and S42. Raising the patch
score would also remove the source-visible yellow stone S69. See the
[source frames and main report](FULL-MATCH-STAGE2-RESULTS.md).

This separate **postscore development** feature measures the neutral-gray
fraction in a band directly beneath each of the three existing coloured-cap
boxes. Its exact crop geometry and HSV bounds are frozen in the
[feature audit](body-band-feature-audit-postscore.json). The candidate feature
is the **maximum** measurable fraction across its three samples. The
[development screen](body-band-screen-development-postscore.json) abstains if
that maximum is below **0.5** or no band is measurable. It preserves every
frozen decision and never creates a new acceptance.

| Recording / interval | Frozen provisional acceptances | After body-band abstention | New abstentions | Minimum measured candidate fraction |
| --- | ---: | ---: | --- | ---: |
| Canada–Czechia full match | 79 | 78 | S96 | 0.428 |
| Canada–Slovakia 1650–2760 s | 17 | 17 | none | 0.790 |
| Canada–Italy 1650–2760 s | 14 | 14 | none | 0.775 |
| Canada–Estonia 1650–2760 s | 17 | 17 | none | 0.606 |
| Canada–Latvia 1650–2760 s | 15 | 15 | none | 0.735 |
| Canada–Scotland 1650–2760 s | 17 | 17 | none | 0.700 |
| **Total** | **159** | **158** | **1** | — |

The [six-recording summary](body-band-transfer-summary-postscore.json) checks
these counts, distinct source hashes, the same threshold, and every input
artifact hash. On the exposed full match, S96's maximum is 0.428, while S143's
is 0.685; thus this rule removes **one of the two** source-reviewed accepted
false-positive paths. The lowest reviewed true-stone control here is S42 at
0.698. All 80 accepted candidates in the five other recording intervals were
left unchanged, but they are still provisional rather than independently
verified throws. The threshold was selected after inspecting this match's
false positives, so these numbers are **development behavior, not precision,
recall or F1**. The original frozen outputs are untouched.

A simultaneous-view check was also tried on accepted left-camera paths S42,
S96 and S143. The [pilot artifact](opposite-view-pilot-postscore.json) shows no
nearby right-camera proposal for the source-visible moving stone S42 in three
registered overlapping samples. The absence of an opposite-view proposal
therefore cannot safely reject a left-camera event under the current camera
geometry and detector. It was **not** added as a gate.

To promote the body-band feature into a robust detector, it still needs
independent exhaustive throw labels, negative examples beyond the exposed
footrest, stone-level checks across changing camera views, and an evaluation
that includes throws missed before the appearance stage. Source inspections
and unchanged provisional counts cannot establish that promotion.
