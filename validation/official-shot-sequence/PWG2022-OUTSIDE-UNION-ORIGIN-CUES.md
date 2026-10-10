# Origin-view cues outside the provisional event union

The [frozen selection](pwg2022-origin-shots-outside-union-plan.json) contains every camera shot that the existing origin model predicted as delivery-like but that no event in the current three-recording provisional union names as a source shot. The [unchanged source-only scan](pwg2022-origin-shots-outside-union-cues-development.json) checked all 71 shots for a held-to-motion cap passage and applied the existing ice-context rule. No counter, official shot number, cue result, or colour was used to select the shots.

| Recording | Origin-predicted shots outside union | Shots with raw passages | Shots with one ice-supported passage |
| --- | ---: | ---: | ---: |
| Switzerland | 44 | 2 | 1 |
| China | 24 | 1 | 1 |
| Slovakia | 3 | 0 | 0 |
| **Total** | **71** | **3** | **2** |

The [source frame panel](pwg2022-outside-union-origin-cues-review.jpg) shows the three raw cases. Swiss **S392** visibly carries a red stone from a held position into delivery; its ice-supported cue is at **5072.4 s**. China **S216** similarly shows a red stone and a cue at **2665.4 s**. Both camera shots are absent from the union, and neither release window overlaps a union event. The two [machine-readable rescue proposals](pwg2022-outside-union-release-rescue-proposals-development.json) preserve those source observations with no counter or official shot assignment. Swiss **S394** is a player close-up; its raw red cap-like trigger at 5114.8 s fails the existing ice check (below-ice fraction 0.0794) and is not proposed.

The [receiving-view audit](pwg2022-outside-union-receiving-view-development.json) verifies a broadcast cut after each origin shot and applies the existing 12-second post-cut colour-motion scanner. Both cases yield exactly one strict red track and no strict yellow track: Swiss S392 has a red track at 5084.2–5089.8 s; China S216 has one at 2670.8–2681.2 s. Both camera-motion registrations remain unresolved. Matching colour and timing support a two-view event hypothesis but do **not** prove persistent physical stone identity.

Nearby delayed-counter chronology and the official shot list make these especially relevant recall candidates: S392 is between the Swiss end-five S13 counter and the end-six first-shot counter, while S216 is between the China end-three S15 counter and the end-four first-shot counter. The source panel suggests deliveries, but this is a postscan interpretation and **not** an independent physical throw label or a verified official shot mapping. The [frozen baseline union](pwg2022-provisional-event-evidence-union-development.json) remains at 356 candidates. A separate [additive v2 union](pwg2022-provisional-event-evidence-union-v2-source-rescues-development.json) has 358 candidates, including these two source-only review cases with physical identity explicitly unverified.

This scan does not estimate false-positive rate. “Outside the union” does not mean “no throw”; in fact the two supported cases are potential misses. It also does not estimate recall, because the origin model can miss delivery views. The next useful checks are source review of full event chronology and whether each receiving track can be distinguished from camera motion and other stones.

Run `PYTHONPATH=. feasibility/scripts/python.sh prototype/scripts/audit_pwg2022_origin_shots_outside_union.py` on a clean checkout to generate the selection and first scan. The script preserves its first scan instead of overwriting it. Run `python prototype/scripts/propose_pwg2022_outside_union_releases.py` to verify the hashed proposal export.
Run `PYTHONPATH=. feasibility/scripts/python.sh prototype/scripts/audit_pwg2022_outside_union_receiving.py` to reproduce the two-view audit.
