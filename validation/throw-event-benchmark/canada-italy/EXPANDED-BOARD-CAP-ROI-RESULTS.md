# Expanded right-panel board-cap ROI: source counterexample and transfer

The [predeclared post-review plan](EXPANDED-BOARD-CAP-ROI-PLAN.md) changed only the cap candidate ROI's upper edge from **y=155** to **y=135** in the same 640×360 source frame. The trigger was the [all-12 Italy clear-tier source review](right-large-cap-clear-delta-source-review/manifest.json): a red stone around `(432,155)` stays visibly in place throughout S142, S144, S145 and S146 ([six-frame zoom per candidate](right-large-cap-clear-delta-source-review/edge-zoom.jpg)), yet the fixed crop reported that red cap as appearing or disappearing. Thus **at least four “clear-context changes” were detector/ROI errors**, not observed physical stone moves. The expanded-ROI probe retains that same red cap on both sides of all four events. S145 becomes a no-visible-change row; S142, S144 and S146 still have *other* apparent cap changes, so they cannot be called clean transitions.

The expanded rule was then applied to the full Italy and Estonia supported runs with unchanged event times, three-frame timing, scene guards, cap stability, image matching and context thresholds. The [Italy pre](right-large-cap-full-pre-left-partial-caps-expanded-roi.json), [Italy post](right-large-cap-full-post-left-partial-caps-expanded-roi.json), [Estonia pre](../canada-estonia-2024/right-large-cap-full-pre-left-partial-caps-expanded-roi.json) and [Estonia post](../canada-estonia-2024/right-large-cap-full-post-left-partial-caps-expanded-roi.json) scans retain the original fixed-ROI artifacts separately.

| Recording and diagnostic | Fixed ROI | Expanded ROI |
| --- | ---: | ---: |
| Italy stable pre-cap proposals | 92 | 156 |
| Italy stable post-cap proposals | 83 | 133 |
| Italy comparable pre/post windows | 88 | 88 |
| Italy clear-context image-change review | 12 | 9 |
| Italy cluttered image-change review | 31 | 56 |
| Italy no visible cap change | 45 | 23 |
| Estonia stable pre-cap proposals | 141 | 182 |
| Estonia stable post-cap proposals | 112 | 139 |
| Estonia comparable pre/post windows | 99 | 99 |
| Estonia clear-context image-change review | 14 | 10 |
| Estonia cluttered image-change review | 52 | 61 |
| Estonia no visible cap change | 33 | 28 |

The comparable-window counts are unchanged because the scene comparison ROI and timing guards were fixed. The expanded [Italy image deltas](right-large-cap-full-pre-post-partial-cap-deltas-expanded-roi.json) and [context triage](right-large-cap-full-pre-post-cap-delta-context-triage-expanded-roi.json), with their [Estonia delta](../canada-estonia-2024/right-large-cap-full-pre-post-partial-cap-deltas-expanded-roi.json) and [triage](../canada-estonia-2024/right-large-cap-full-pre-post-cap-delta-context-triage-expanded-roi.json) transfers, show the tradeoff: more of the house is visible, but many additional coloured candidates lie near players or other clutter. The fixed-ROI clear tiers also had **9/12 Italy** and **9/14 Estonia** rows with at least one changed cap within 8 px of an ROI edge. This 8 px proximity check was calculated after Italy review and is a diagnostic, not a predeclared acceptance rule.

Neither ROI should be treated as a reliable settled-board extractor. The narrow crop silently loses real visible stones at its edge; the expanded crop adds many cluttered cap changes. A better next iteration needs camera-specific house geometry, explicit player/occlusion handling and source validation of any board-change decision. All counts here are image proposals on exposed development matches, not stone-transition precision/recall, verified scoring states, or simulation-ready outputs.
