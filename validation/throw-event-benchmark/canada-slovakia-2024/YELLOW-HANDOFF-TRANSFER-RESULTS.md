# Fixed yellow handoff transfer to Canada–Slovakia

The [predeclared 1990–2070 s window](YELLOW-HANDOFF-TRANSFER-PLAN.md) was
processed with the same settings as the Korea T11 development handoff. The
[generic runner](yellow-handoff-1990-2070-development.json) first reproduced
the Korea body, cap and joined-path artifacts exactly in a separate
[regression run](../canada-korea-2024/yellow-handoff-generic-regression.json).
It then scanned the Slovakia source without reading any target path positions
or source-review labels.

The Slovakia scan produced **164 yellow body proposals**, **13
yellow-handle-supported boxes**, one upward image path at **2034–2046 s**,
and **zero positive cap points** in the complete 80-second window. The
[six-frame source sheet](yellow-handoff-1990-2070-source-review.jpg) and its
[manifest](yellow-handoff-1990-2070-source-review.json) show those body
boxes on one visible yellow stone moving toward the house. The body path
spans 360 px vertically in the original 1080p view. This is a successful
partial *body-template* transfer, but the fused tracker adds no observations
and produces no visual-stop bracket on this recording.

The [postresult stage audit](yellow-handoff-cap-stage-postresult.json) uses
the detected body-path positions only to diagnose the cap failure. Nearby
raw yellow colour proposals exist in **all 13** path frames, but none passes
the frozen China-trained side-view cap-context threshold of zero. Their best
scores range from about **−2.62 to −0.61**. Thus, as in the Korea learned-box
test, candidate generation is available but the appearance classifier does
not transfer reliably. Lowering the model threshold now would be
postresult fitting and has an unmeasured false-positive cost.

This interval was selected using an earlier, developer-reviewed yellow
passage; the six-frame sheet and stage audit were also reviewed by the
developer. It is **not** independent throw validation. The result shows a
specific cross-recording failure of the cap handoff, and a separate partial
success of the body template. It proves neither physical stone identity
through settling nor full-video event precision, recall or F1. Board state,
metric trajectory, spin and simulation readiness remain unknown.

Reproduce with:

```sh
feasibility/scripts/python.sh prototype/scripts/transfer_yellow_template_cap_handoff.py --target korea-regression
feasibility/scripts/python.sh prototype/scripts/transfer_yellow_template_cap_handoff.py --target slovakia-transfer
feasibility/scripts/python.sh prototype/scripts/render_slovakia_yellow_handoff_transfer.py
feasibility/scripts/python.sh prototype/scripts/diagnose_slovakia_yellow_cap_stage.py
```

The next appearance component should explicitly cover the side-view scales
and broadcast styles represented by Korea and Slovakia, and be frozen before
another recording is opened. Temporal tracking and camera-handoff rules
must then be evaluated against complete, independently labelled videos.

A **postresult** [raw yellow-contour continuation](yellow-contour-continuation-development.json)
instead follows the source-visible stone from the last body match at 2046 s
through a visual-stillness bracket at **2048–2049 s**, confirmed to 2051 s.
The [review sheet](yellow-contour-continuation-source-review.jpg) shows the
selected contour on the apparent stone. The +18 px image body proxy and
association cost were chosen after reviewing Korea and Slovakia, so this
does not repair the first-transfer failure above or constitute held-out
validation. A subsequent [Estonia first transfer](../canada-estonia-2024/YELLOW-CONTOUR-FIRST-TRANSFER-RESULTS.md)
then exposed an opposite image-motion direction and ROI truncation.
