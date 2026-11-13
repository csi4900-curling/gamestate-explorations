# Full-match right-camera association variants

Three unchanged right-colour association variants were run over the same 0–7058 s Latvia source. The [one-to-one inventory comparison](full-right-association-variant-comparison-development.json) uses only claimed colour, image direction and passage times within eight seconds. These are proposal comparisons, not physical throw matches.

| Association and proposal rule | Raw tracks | Review proposals | Nearby proposal for 19 source-reviewed stone-pixel paths |
| --- | ---: | ---: | ---: |
| [One-second greedy](full-right-area-first-transfer.json) | 485 | 100 | 18; misses R008 |
| [Two-second greedy](full-right-area-gap2-development.json) | 555 | 118 | 19 |
| [Two-second global assignment](full-right-global-area-development.json) | 564 | 114 | 18; misses end-6 A452 |
| [Global tracks with quiet-separated later spans](full-right-global-multi-episode-development.json) | 564 | 118 | 19 |

The [19-witness timing audit](full-right-source-stone-witness-coverage-development.json) contains the 16 previously source-reviewed moving-stone-pixel paths in displayed end 6, the source-reviewed A008 and A367 paths, and the older R008 stone-pixel path. These were selected or reviewed after detector output by the same agent. Coverage means only that a proposal of the same colour and image direction occurs within eight seconds; it is **not** measured throw recall or verified same-stone identity. The [multi-episode extension](full-right-global-multi-witness-coverage-development.json) shows exactly which witness it restores.

Global assignment reconnects R008, but its raw track **A530** also contains the same eight source observations as the baseline moving-stone path **A452** at 6400–6407 s. Its first proposal is at 6376.131 s and its extractor stops after that first span, leaving no proposal near A452 at 6403.727 s. The [quiet-separated extractor](../../../prototype/right_multi_episode_span.py) preserves all 114 first spans and proposes four later spans; A530's second passage is at 6404.245 s, restoring that timing window. The [source sheets](full-right-global-later-episode-source-packet/manifest.json) and [pixel audit](full-right-global-later-episode-source-audit.json) show that **three** added spans mix stone, person or equipment pixels; the A530 span shows the later moving red stone body but its long-track identity is unresolved.

The wider-gap variants therefore recover a documented source-visible path but also increase review load and admit identity splices. The global assignment alone is **not** a safe replacement for the one-second version: it loses an already reviewed moving-stone timing cue at A452. Adding later spans recovers that cue but does not make the resulting tracks verified events. The existing [R008 full-gap audit](R008-GAP2-FULL-RESULTS.md) details the separate greedy-gap tradeoff. None of these variants has independent complete-match throw labels, complete settled boards or simulation-ready metric paths; no precision, recall or F1 is claimed.
