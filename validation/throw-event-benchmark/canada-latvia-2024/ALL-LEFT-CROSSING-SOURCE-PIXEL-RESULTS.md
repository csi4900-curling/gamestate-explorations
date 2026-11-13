# Latvia full-match left-crossing source-pixel audit

All **119 saved raw left-camera crossing tracks** in the Latvia full-match run now have crossing-local source-pixel reviews. These are object reviews made by the development agent after detector/model output, **not independent physical-throw labels**.

| Detector disposition | Clear stone-body track crops | Person/equipment track crops | Ambiguous crops | Total |
| --- | ---: | ---: | ---: | ---: |
| Accepted | 70 | 1 | 1 | 72 |
| Withheld | 0 | 45 | 2 | 47 |

The [accepted-crossing audit](all-positive-patch-source-audit/manifest.json) and [negative-score audit](all-negative-patch-source-audit/manifest.json) cover the 72 accepted tracks. The [withheld audit](withheld-left-crossing-patch-source-audit/manifest.json) covers all 47 withheld tracks, with [six contact pages](withheld-left-crossing-patch-source-audit/withheld-page-1.jpg) and three source-frame crops per track. One short withheld track (S44) uses its nearest three observed points because symmetric crossing samples are unavailable. The [combined 147-candidate handoff](full-match-area-censored-candidate-handoff-all-left-source-reviewed-development.json) preserves all earlier candidate IDs, review tiers, and null physical-throw counts.

Within the **saved, tracked crossing objects**, screening did not withhold a clearly visible stone body in this same-agent review. This is useful evidence about that specific screen. It does not establish full-match event recall: stones can be missed before a crossing track exists, during routing gaps, in another view, or outside the sampled crop. The two withheld ambiguous tracks remain unresolved.

The frozen China-trained patch model calls **32 of 47 withheld tracks stone-like**, including 30 that the source-crop review classes as person/equipment. The model therefore remains unsuitable as an automatic hard veto or rescue gate across this recording. Its scores are preserved in the [withheld score file](withheld-left-crossing-patch-score-development.json).

The current ledger still has **96 development-tier possible event proposals**, `physical_throw_count_verified: null`, and no simulation-ready states. Next validation needs an independently checked full-match throw sequence and camera-coverage review, then same-stone continuity to a settled board. Pixel classes alone cannot certify segmentation F1 or game state.

The [packet builder](../../../prototype/scripts/build_latvia_withheld_crossing_patches.py), [audit builder](../../../prototype/scripts/audit_latvia_withheld_crossing_patches.py), and [ledger exporter](../../../prototype/scripts/export_latvia_all_left_crossing_source_pixels.py) verify source and artifact fingerprints. The source review is reproducible as a frozen record; the human visual judgments themselves are not automated ground truth.
