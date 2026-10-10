# Does 1080p recover missed crossing boxes?

The [360p public-box probe](PUBLIC-BOX-CROSSING-RESULTS.md) suggested that tiny
caps might explain the stone-box misses. We tested the *same selected passage
crossings* where aligned original 1080p clips exist, at −0.2, 0, and +0.2 s.
The [comparison script](../../../../prototype/scripts/audit_highres_crossing_boxes.py)
uses identical HSV cutoffs and proportionally scaled contour-area floors and
box sizes, then applies both frozen public patch models to source-resolution
patches. No event decision or frozen threshold changed. Resized-frame mean
absolute differences were 4.0–4.8 intensity levels for Scotland and
5.9–6.1 for Latvia, supporting the time alignment of these samples.

| Selected crossing, source review | 360p clip model accepted in 3 samples | 1080p clip model accepted in 3 samples |
| --- | ---: | ---: |
| Scotland S56, visible yellow stone | 1 | 2 |
| Scotland S59, visible red stone | 0 | 0 |
| Scotland S63, visible yellow stone | 1 | 0 |
| Scotland S58, visible red jersey logo | 0 | 0 |
| Latvia S45, visible red player/head | 0 | 0 |

The [Scotland](scotland24-bridged-development/highres-box-probe.json) and
[Latvia](latvia24-full-v1/highres-box-probe.json) artifacts retain every raw
contour, score, threshold decision, frame-alignment error, and source/model/code
hash. At Scotland S59 the 1080p frame has a large same-colour cap contour and
12 local box proposals at each sample, yet all clip scores remain below its
fixed 1.34 threshold. S63 also has 12 proposals in each 1080p sample but loses
its one 360p positive. High resolution helps S56 and does not consistently
recover visible stones. The older image model accepts none of these three
stone crossings at 1080p.

These five prediction-targeted cases cannot estimate match-wide recall or
precision. The clip model was trained and thresholded on different imagery;
the 1080p experiment is not a calibrated transfer. It does, however, rule out
the simple claim that source resolution alone fixes these particular misses.
A successor verifier needs training/evaluation for far-small stones and a
separate ground-contact/temporal identity cue. Its event-level threshold must
be set on development footage and tested against independent complete-match
annotations before it can veto or promote throws.
