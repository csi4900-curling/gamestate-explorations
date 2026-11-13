# Canada–Norway isolated-edit transfer

This is a **development transfer run**, not independently labelled throw validation. The Korea–China 2× temporal isolation rule was applied unchanged to the 10 previously frozen Norway possible edits. Seven passed. Adding those seven points to the 708 conservative hard cuts produced 716 camera-shot windows instead of 709, while the frozen first-pass outputs remained unchanged.

The [cut-effect audit](cut-effect-audit.json) shows that five of the seven cuts left adjacent origin windows negative (`000`: old, left, right). Two moved an existing positive origin into the right-hand window (`101`). None changed a previously negative origin window into a positive one. The final event ledger stays at **142 candidates**, including **100 counter-backed candidates**, matching the first pass. The [ledger comparison](ledger-comparison.json) finds one counter-backed change: B45's yellow release window shortened from 3065.8–3111.2 s to 3086.4–3111.2 s. All other counter-backed colours and windows remain the same. The [multiscale handoff](multiscale-event-handoff.json) preserves both B45 windows as alternatives; no exact release time or physical identity is promoted.

This result shows that isolated image-change spikes alone are a weak reason to add a cut globally. It does not prove the seven proposals are false cuts; they may improve camera boundaries without changing event count. There are no independent video-timestamp labels here, so precision, recall and F1 remain unknown. The broadcast counter is evidence from the source video, not independent physical throw ground truth.

The [visual-only patch diagnostic](visual-only-patch-evidence.json) finds at least one stone-like cap track for 24 of 42 unbacked candidate windows; 18 lack such support. It does not change the candidate ledger or verify a physical throw.

The [joined visual-only cue table](visual-only-evidence-patterns.json) records nine candidates with both stone-like patch and unique colour-compatible held-release passage, 15 with appearance only, two with release only, and 16 with neither. All remain provisional.
