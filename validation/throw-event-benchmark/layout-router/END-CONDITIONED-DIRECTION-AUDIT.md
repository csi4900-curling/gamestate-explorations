# End-conditioned candidate direction: development audit

The Czech full-match run produced **147 raw passage candidates** and **96
context-confirmed candidates**. The 96 total equals the nominal number of
deliveries in its six completed ends, but this is **not** a throw-recall result:
the candidate list includes source-reviewed non-stone motion, and its per-end
distribution does not match 16 deliveries per end. The reproducible
[candidate inventory](czech24-full-camera-motion-v1/end-conditioned-candidate-inventory.json)
places candidates only inside repeated broadcast end-marker runs and leaves
transition times unassigned.

| Czech broadcast end | Marker-hit interval (s) | Raw candidates | Context-confirmed | Confirmed image direction |
| --- | ---: | ---: | ---: | --- |
| 1 | 120–810 | 26 | 13 | 12 negative Y, 1 positive Y |
| 2 | 830–1940 | 21 | 16 | 16 positive Y |
| 3 | 1970–3090 | 24 | 15 | 15 negative Y |
| 4 | 3120–4040 | 21 | 15 | 15 positive Y |
| 5 | 4060–5260 | 26 | 17 | 16 negative Y, 1 positive Y |
| 6 | 5320–6330 | 16 | 15 | 15 positive Y |

Thirteen raw candidates lie outside the six stable marker-hit intervals;
five of those are context-confirmed. They include early and transition-gap
events and a post-marker event. They are **not** assigned to a physical end.
The [direction audit](czech24-full-camera-motion-v1/end-conditioned-motion-direction-development.json)
finds only two opposite-direction confirmed paths within the stable runs:
S18 in end 1 and S103 in end 5. The
[unmarked source-frame packet](czech24-full-camera-motion-v1/direction-exception-source/REVIEW.md)
shows that both follow red features moving with players or wheelchairs. This
is same-agent source review, not an independent reference set.

Reviewing long gaps among the end-1 confirmed candidates found the opposite
error as well: [S04 and S13 are source-visible red-stone paths withheld by
the `large_surrounding_motion` context gate](czech24-full-camera-motion-v1/WITHHELD-STONE-SOURCE-REVIEW.md).
The raw detector proposed both, and the lossless triage retained them for
review, but they disappear if `events.json` is treated as the final throw
list. This is why end counts and directional consistency should guide
review, not serve as a validated event classifier.

The [Latvia transfer audit](latvia24-1650-2760-raw-context-v1/end-conditioned-motion-direction-development.json)
checks the same image-direction idea against a second 2024 recording. Its
stable broadcast end-2 marker extends through 1900 s and end 3 begins at
1920 s. In the analyzed 1650–2760 s interval, all five context-confirmed
candidates under end 2 move positive Y; all eleven under end 3 move negative
Y. Three raw negative-Y proposals at 1910–1914 s fall in the marker
transition gap and were withheld by the existing context filter. Under the
stable end-3 marker, three opposite-direction raw candidates were also
withheld. These associations are descriptive; the context-confirmed
candidates have no independent physical-throw labels.

Direction consistency is therefore a useful **review priority or soft
feature**, conditioned on a reliable end and camera state. It cannot yet be
a hard veto. Broadcast graphics can lag play, the view may reverse or switch,
and a true stone may change image direction after contact. More importantly,
rejecting an opposite-direction candidate without a physical reference would
risk recall. The next validation step is to review complete throw intervals
and their candidate/withheld paths against source video, then score precision
and recall on an independently labeled recording.

Recreate the immutable audits with
`feasibility/scripts/python.sh prototype/scripts/reconcile_czech_candidates_by_end_marker.py`,
`feasibility/scripts/python.sh prototype/scripts/audit_czech_end_motion_direction.py`,
and
`feasibility/scripts/python.sh prototype/scripts/audit_latvia_end_motion_direction.py`
after moving their respective output JSON files aside. Each artifact pins its
inputs and audit code by SHA-256. The Latvia audit also pins the marker-run
summarizer.
