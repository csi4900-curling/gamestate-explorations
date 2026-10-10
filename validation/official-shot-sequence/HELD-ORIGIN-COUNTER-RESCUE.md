# Held-origin recovery proposals across 2022 recordings

The [reproducible development audit](pwg2022-held-origin-counter-rescue-development.json) adds a separate proposal lane to the existing full-video cap-fusion ledgers. It reuses the previously frozen held-cap passages and the later ice-context gate. A shot is proposed only when its unique held-cap passage is over bright low-saturation ice, the shot is absent from the cap-fusion events, and exactly one as-yet-unassociated delayed counter of the **same colour** follows the release cue within 45 seconds. If two passages compete for one counter, either passage fits multiple counters, or no counter fits, the rule abstains. It does not modify the frozen cap-fusion ledgers.

| Recording | Existing cap-fusion events | Unassociated counters | Ice-gated held passages | New provisional proposals |
| --- | ---: | ---: | ---: | ---: |
| Sweden–Switzerland | 115 | 10 | 1 | **0** |
| Canada–China | 112 | 24 | 4 | **3** |
| Slovakia–USA | 116 | 10 | 0 | **0** |

The China proposals are `S103/B22` yellow (held cue 1412.6 s), `S274/B56` yellow (3394.4 s), and `S278/B57` red (3459.8 s). The China `S216` passage and Swiss `S392` passage remain unmatched visual cues. If added, the China candidate count would rise from 112 to 115 and unassociated delayed counters would fall from 24 to 21. These are *pipeline coverage counts*, not event precision or recall. The other two recordings offer no positive same-rule rescue case, so this exercise does not establish cross-recording recovery accuracy.

`S278/B57` matters for the [China board handoff](CHINA-BOARD-EVENT-COVERAGE.md): its five-stone partial board remains a real video observation, while the cap-fusion event set omits its counter. The held-cap cue supplies a provisional earlier event candidate for that counter. It still does not prove which observed board stone was delivered or whether the board changed as a result. `B26`, the other omitted board-bearing counter, remains unresolved by this lane.

The held-cap motion thresholds were developed after inspecting missed China deliveries, and the ice gate was chosen after a Swiss clothing false positive. This is therefore a **postscore development result on exposed recordings**. A white object or another stone may still mimic the passage, the broadcast counter is delayed, and no physical stone identity or exact release time is verified. The proposal JSON marks every added event `simulation_ready: false`; source-only coverage and independent full-match event precision/recall remain necessary before promotion.

Run `python prototype/scripts/propose_2022_held_origin_counter_rescues.py` from the repository root to verify the artifact exactly against the recorded hashes. Focused tests cover unique, ambiguous, competing and unmatched joins.
