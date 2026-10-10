# Canada–Italy 2024: fixed repaired-motion transfer

**The Estonia-developed repair transfers partway, but still misses three throws.** Against 17 exposed coarse delivery windows, the frozen repaired filter retained **14 TP / 0 FP / 3 FN**: precision 1.00, recall 0.824, F1 0.903. There were no colour mismatches among the matched events. The unchanged 24-candidate passage baseline found all 17 windows with seven extras (17/7/0, F1 0.829). Thus the filter removed the seven extras but also removed three real candidates. It remains below the high-recall target and is not a robust finished event detector.

The [pre-inference plan](CANADA-ITALY-2024-REPAIRED-MOTION-TRANSFER-PLAN.md) fixes the candidate set, parameters, code hashes, and model before the 1080p Italy interval was acquired. The high-resolution copy is 1920×1080, 30 fps, 1110.1 s, SHA-256 `b5235f955c7f23084bbee543ccd2720db98957c2b69826fd0909fd6e35107a62`. The [alignment check](canada-italy-2024-highres-alignment-transfer.json) chose zero source-time adjustment at six sampled times from 1750 to 2700 s. The 360p match, candidate set, and coarse same-agent labels had all been exposed earlier; this is a fixed-rule cross-recording **development transfer**, not independent or full-match validation. The reserved unseen end was not used.

| Stage | Unique selected paths | Meaning |
| --- | ---: | --- |
| [Raw 0.5 s receiving scan](canada-italy-2024-candidate-centric-motion-frozen-repair-transfer.json) | 5 / 24 | Candidate time, colour, expected view only |
| [Still-camera registration hold](canada-italy-2024-candidate-registration-hold-frozen-repair-transfer.json) | 11 / 24 | 95 rejected samples borrowed a nearby transform after lower-ice similarity checks |
| [Bounded missing-observation gaps](canada-italy-2024-candidate-motion-with-gaps-frozen-repair-transfer.json) | 14 / 24 | Skip only registration-abstention samples, at most 4.1 s |
| [Timed-path deduplication](canada-italy-2024-candidate-shared-motion-dedup-frozen-repair-transfer.json) | 14 / 24 | No shared path met the frozen duplicate rule |
| [Patch appearance and final screen](canada-italy-2024-candidate-motion-patch-screen-frozen-repair-transfer.json) | 14 / 24 | All 14 selected paths had at least one positive sampled cap patch |

The [first fixed-rule score](canada-italy-2024-repaired-motion-transfer-score.json) preserves the candidate baseline and final screen in one artifact, including source, candidate, reference, code, and scorer hashes. Event matching uses broad windows; colour disagreements are reported separately. It does not measure release-time or settle-time accuracy.

## Missed-window diagnosis (after scoring)

All three missed windows have a correctly coloured passage candidate. The final screen withholds each because the provisional path selector cannot start a sufficiently long path at its fixed far-entry boundary. The following is a retrospective inspection of the preserved proposal coordinates; it does **not** change the first transfer score.

| Window / candidate | Evidence in frozen receiving samples | Failure |
| --- | --- | --- |
| I02 / S03, yellow, left view | Far moving proposal at 1799.0 s, y≈−5.75 m; no moving proposal at 1799.5–1800.0 s; then a moving sequence from 1800.5 s, y≈−3.93 m | The first point is isolated by **registered frames with missing cap detections**. Later points begin past the fixed left entry boundary y=−4.5 m, so cannot start a new path. |
| I07 / S18, yellow, right view | Moving proposal first appears at 2140.0 s, y≈11.70 m, followed by points toward the house; earlier samples show a parked yellow stone or registration abstention | The first usable moving point is already inside the right entry boundary y=12 m. The still-shot hold rejects the intervening changed-view frames, correctly leaving them unknown. |
| I08 / S19, red, right view | Moving stone is proposed from 2184.5 s, y≈17.83 m, but is absent in some registered samples at 2186.0 and 2188.5 s; another sequence starts at 2189.0 s, y≈7.92 m | Missing cap detections split the initial path. The later sequence begins inside y=12 m and cannot restart. |

The fixed entry boundary made sense as a conservative way to avoid parked stones, but it is a recall bottleneck when the first far observation is late or the visible path fragments. Relaxing it now would be an **Italy-informed postscore change**. Any such change must be evaluated on all exposed development matches for false paths, then frozen before another recording. The path must still carry source-visible motion and stone appearance evidence; a lower threshold alone could accept player gear or parked stones.

A reproducible [postscore entry-gate sensitivity check](italy-estonia-entry-gate-sensitivity-postscore.json) confirms the tradeoff. With the same held samples and gap rule, changing the left/right start boundaries from **−4.5/12 m** to **−2/4 m** recovers S03, S18, and S19, but also admits false S14 and turns previously accepted S31 into an ambiguous path. Italy's motion-only score changes from **14/0/3** to **16/1/1**; the remaining miss is I16. Estonia's motion-only score stays **17/1/0** (the extra S24 is the duplicate later removed by deduplication). This experiment does not rerun the patch or dedup stages and is neither the frozen Italy result nor a validated replacement rule. It shows why simply moving the line cannot solve the recall problem without a better way to maintain path identity through detections and ambiguity.

Nothing here establishes physical stone identity through the camera handoff, calibrated metric trajectory error, complete post-throw boards, or simulation-ready game state. Those remain downstream validation gates.

A later [conditional cap-dropout rescue](CANDIDATE-DROPOUT-RESCUE-DEVELOPMENT.md) fits this exposed interval at 17/0/0. It was designed after this fixed transfer was scored and does not replace the 14/0/3 transfer result.
