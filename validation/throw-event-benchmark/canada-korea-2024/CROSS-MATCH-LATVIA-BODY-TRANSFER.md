# Frozen Latvia body templates on Canada–Korea T11

The 90-second [Canada–Korea 1080p clip](../../../prototype/continuous/clip.mp4)
covers source time 2260–2350 s and includes the previously investigated T11
yellow throw. The [transfer audit](latvia-body-template-transfer-v2-development.json)
ran the unchanged Latvia yellow and red grey-body templates, handle-colour
screens, score threshold and right-ice search bounds at 1 Hz across the **full
clip**. Template, clip, T11 track and runner hashes are pinned. This is a
cross-recording development check, not independent event scoring.

The frozen yellow lane finds **one upward path at 2308–2311 s** with four
observations and 232 px of upward image displacement. The
[marked source sequence](latvia-template-t11-source-review.jpg) and
[manifest](latvia-template-t11-source-review.json) show that those boxes
follow a single yellow stone moving toward the house. The red lane produces
no handle-supported path. Thus the lower-ice stone-body cue **does transfer
partially** to this different match.

The yellow stone remains source-visible at 2312–2313 s, but the frozen body
matcher no longer returns a supported box. Near the existing provisional T11
cap track, local yellow-template scores at 2312.5, 2313.0, 2313.5 and
2314.0 s are **0.488, 0.513, 0.504 and 0.524**, all below the frozen
0.55 score floor. As the stone continues up-ice, the expected body centre
leaves the search region, which starts at 1080p image y = 520. The detector
therefore cannot supply a continuous receiving path or a visual stop for T11.
The +15 px cap-to-body offset used for this local score diagnosis was chosen
after source inspection; it is not part of the frozen detector.

This result separates two limitations: the appearance score drops below the
threshold while the stone is still in view, and the fixed search geometry
subsequently excludes it.

## Postreview score and search-area ablation

The [reproducible ablation](t11-score-roi-ablation-development.json) varies
only the body score floor (0.55 or 0.45) and search-area top edge (image y =
520 or 400). It uses the same Latvia yellow template, colour-handle gate,
1 Hz sampling, peak limit and path linker over the same full 90-second Korea
clip. The frozen setting reproduces the earlier **29 body proposals, four
handle-supported proposals and one upward path exactly**.

At 0.45 with the original area, the same visible stone is followed from
**2308 through 2314 s**, as shown by the [source-review sheet](t11-score-roi-source-review.jpg)
and its [manifest](t11-score-roi-source-review.json). Widening the area alone
adds no continuation. Combining the wider area and lower floor still ends at
2314 s: the stone is visible at 2315 s, but no supported proposal joins the
path. In a local diagnostic around the provisional T11 track, the best body
score at 2315 s is about **0.431**, below even the lowered floor. This local
diagnostic uses the prior track to find where to look and is not a detector
result.

| Search area / score floor | Body proposals | Yellow-handle proposals | Upward linked paths | T11 path |
| --- | ---: | ---: | ---: | --- |
| Original / 0.55 | 29 | 4 | 1 | 2308–2311 s |
| Original / 0.45 | 370 | 97 | 1 | 2308–2314 s |
| Wider / 0.55 | 29 | 4 | 1 | 2308–2311 s |
| Wider / 0.45 | 458 | 101 | 1 | 2308–2314 s |

The lower cutoff recovers three T11 samples but creates many extra isolated
proposals. The absence of another *linked upward path* in this clip is not a
precision measurement; those extra proposals and any future recording may
still produce false events. These variants were chosen after seeing T11, so
none is a held-out result or a reason to change the frozen detector yet. The
next detector needs a stronger stone representation and view-aware tracking
to retain a moving stone as its appearance and scale change. An untouched
recording with independent throw labels is required before claiming
cross-match recall, and continuous receiving tracks are required before
claiming simulation-ready trajectories. The [two existing learned stone-box
models](KOREA-T11-LEARNED-BOX-TRANSFER.md) also miss this moving stone: the
colour proposal stage covers it, but neither frozen appearance classifier
accepts a nearby box in the 12 examined one-second samples.

Reproduce with `feasibility/scripts/python.sh prototype/scripts/audit_korea_t11_score_roi.py`
and `feasibility/scripts/python.sh prototype/scripts/render_korea_t11_score_roi.py`.
