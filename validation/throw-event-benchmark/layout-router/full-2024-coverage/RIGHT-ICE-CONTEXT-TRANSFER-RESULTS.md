# Fixed ice-context cue: Canada–Slovakia transfer

The [predeclared plan](RIGHT-ICE-CONTEXT-TRANSFER-PLAN.md) fixed the right-view proposal rule and the non-ice ring threshold at **0.25** before this clip's right proposals or scores were inspected. This was a development transfer on source seconds 1650–2760 of the 2024 Canada–Slovakia recording, not an independent detector evaluation. The source clip SHA-256 is `cd5799da6d851e01c365b5f4aeeb2fb10b068e6d726d273ac129ad8f87330077`.

The [probe](../../canada-slovakia-2024/right-bidirectional-transfer-development.json) found **50 raw colour tracks** and **16 bidirectional review paths**. All 16 were rendered into four [source sheets](../../canada-slovakia-2024/right-bidirectional-source-review/manifest.json), each showing the first, passage-nearest and last sampled frame. The developer reviewed those sheets and saved [short-prefix source classes](../../canada-slovakia-2024/right-bidirectional-source-review/source-prefix-classes.json) *before* running the fixed [ice-context scorer](../../canada-slovakia-2024/right-ice-context-transfer.json).

| Source-visible tracked prefix | Isolated ice context (≤0.25) | Cluttered review (>0.25) | Total |
| --- | ---: | ---: | ---: |
| Moving stone | 13 | 0 | 13 |
| Person / wheelchair | **2** | 1 | 3 |
| Total | 15 | 1 | 16 |

The two isolated-person failures are **B008** at 1778–1781 s (median non-ice score 0.075) and **B033** at 2312–2315 s (0.058). Both tracks follow a wheelchair athlete's head over bright rink ice. The cluttered-person case **B016** scores 0.439. The moving-stone scores range from 0.009 to 0.021. This is a clear failure of the proposed *isolation-based rejection* on a previously unscored clip: a head can have low surrounding non-ice fraction even when the entire path is a person. The cue remains a review tier, never a stone identity verdict.

The next object check must use evidence that distinguishes the tracked cap from a head, such as the body/wheelchair support beneath it, stone body geometry, or a verified cross-view stone link. It should abstain where these cues are obscured. A lower threshold between 0.021 and 0.058 would separate this *exposed set*, but choosing it now would fit the failures after inspection and offers no evidence of transfer. Any new rule must be assessed on additional source-reviewed recordings and ultimately on independently labelled complete ends before claiming physical-event precision, recall or F1.

The scanner reads one frame per source second through the declared 1650–2760 s interval. OpenCV reports 1116.03 s from container frame-count metadata, while the intended clip interval ends at local 1110 s; an unbounded first scan reached an undecodable later frame and wrote no output. The [runner](../../../../prototype/scripts/probe_right_bidirectional_clip.py) now requires an explicit `--source-stop` and never samples past the declared source interval. This is a read-boundary correction, not a detector-parameter change.

These classes cover **only the 16 proposed prefixes**, were assigned by the same agent developing the filter, and do not certify physical deliveries or an exhaustive denominator. No new game state, spin, trajectory or simulation parameter follows from this transfer.
