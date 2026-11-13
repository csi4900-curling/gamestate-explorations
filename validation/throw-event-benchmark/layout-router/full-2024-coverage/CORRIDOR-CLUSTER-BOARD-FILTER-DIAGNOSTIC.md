# Can post-event board change filter high-recall throw proposals?

We revisited the **earlier high-recall corridor proposals**, not the later full-match state sequences. The saved Italy corridor contains 24 candidates against 17 source-only coarse delivery windows; Estonia contains 22 against 17. Their existing development scores are **17 TP / 7 FP / 0 FN** and **17 / 5 / 0**, respectively. The references were made by the same agent from sparse source sheets; they are not independent or certified exhaustive.

The [prediction-only feature runner](../../../../prototype/scripts/audit_corridor_candidate_board_change.py) chose the conditional receiving view from each proposal's image-motion direction and tried bounded pre/post cap observations without reading reference labels. It abstained on **all 12 unmatched candidates** because each sat within 35 s of another proposal or an interval boundary. It also abstained on **nine matched candidates**. Thus a per-candidate requirement for measurable board change would discard real coarse-window matches and cannot discriminate the observed extras.

We then grouped proposals of the **same colour and image direction within 25 s total span**, preserving every original member ID. The grouping rule was selected after these recordings were exposed and is only a development diagnostic. A second prediction-only runner sampled before the first and after the last proposal in each group, bounded by adjacent groups. The [saved scores](../../canada-estonia-2024/corridor-motion-cluster-score-postreview.json) and [Italy score](../../canada-italy/corridor-motion-cluster-score-postreview.json) use the first observed proposal time for each group:

| Exposed interval | Original proposals | Groups | Coarse group score | Usable cap comparisons among 17 matched groups | Usable cap comparisons among unmatched groups |
| --- | ---: | ---: | --- | ---: | ---: |
| Canada–Estonia | 22 | 19 | 17 TP / 2 FP / 0 FN, F1 0.944 | 14 | 0 / 2 |
| Canada–Italy | 24 | 20 | 17 TP / 3 FP / 0 FN, F1 0.919 | 15 | 0 / 3 |

Grouping removes duplicate image passages within three Estonia and four Italy candidates in this in-sample comparison. It leaves two and three unmatched groups. Every unmatched group either crosses a scene-change guard or sits too close to another group for uncontaminated sampling; **three matched groups in Estonia and two in Italy also abstain**. The scene guard is not a proof of non-throw motion, and rejecting all abstentions would lose recall. The image-cap delta is therefore retained as state/review evidence, **not** a hard throw acceptance filter.

These scores do not supersede the frozen first-transfer measurements. The 25 s grouping and board-view/scene thresholds were selected after looking at exposed 2024 material, and the sparse coarse windows may miss deliveries. A high-F1 detector still needs an object-level stone/person discriminator, explicit duplicate handling, and complete independent evaluation across layouts and full recordings.

Reproduce features before opening labels with `audit_corridor_candidate_board_change.py` and `audit_corridor_motion_clusters_board_change.py`; then run `score_corridor_motion_clusters.py` against the frozen references. The JSON artifacts retain source, candidate, reference, code and runner hashes.
