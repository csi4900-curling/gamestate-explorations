# Sweden–Switzerland throw-event check

Fixed source interval: 1650–2760 s. Nineteen coarse agent-blind source windows
were frozen before inference; this is a partial-match, same-production check.

| Candidate | Interval TP / FP / FN | Interval P / R / F1 | Point TP / FP / FN |
| --- | --- | --- | --- |
| Frozen first pass, before inspecting misses | 17 / 0 / 2 | 1.000 / 0.895 / 0.944 | 15 / 2 / 4 |
| Revised visual gap and boundary recovery, after inspection | 19 / 0 / 0 | 1.000 / 1.000 / 1.000 | 17 / 2 / 2 |

The revision was developed on this recording. It is an in-sample correction,
not a second holdout. The two recovered events are yellow motion at 1853–1861 s
inside a 38-second graphic gap and red motion at 2753–2759 s with a counter
change visible after the declared interval. The counter bracket is not a
release-time estimate. The point score uses the first observed motion or
graphic bracket start and is consequently a stricter, different claim.

The frozen first output and both score files are retained beside the revised
output and scores. The source-only reference may omit brief or hidden throws,
and the same agent prepared it and developed the detector.
