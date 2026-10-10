# Ice-context tie-break for ambiguous counter-to-shot associations

The [three-recording development audit](pwg2022-ambiguous-counter-ice-tiebreak-development.json) tested a source-visible view-context cue on every delayed counter that still had at least two plausible camera shots after cap-motion alignment. It sampled three interior frames of each candidate shot and measured bright, low-saturation pixels in the center of the lower half. A shot passes only if its existing origin probability is at least 0.2 and its maximum sampled ice fraction is at least 0.25. The rule chooses a shot **only when exactly one option passes**; otherwise it abstains. It changes no event ledger.

| Recording | Multi-option counter abstentions | Unique ice choice |
| --- | ---: | ---: |
| Sweden–Switzerland | 3 | **1** |
| Canada–China | 3 | **0** |
| Slovakia–USA | 4 | **0** |

The sole development choice is Swiss B70. Its high-scoring `S362` close-up has at most 0.063 center-lower ice fraction, whereas `S364` briefly shows the delivery ice at 0.477. Lower-probability intermediate shots fail the origin-probability gate. Source frames show a red delivery in `S364` and red stone travel in `S365`; the existing held-cap scanner found no passage in either competing origin shot. This is a **postscore source review**, not independent ground truth.

The unchanged rule and input hashes were then recorded in the [Norway pre-run plan](norway-ambiguous-counter-ice-tiebreak-first-plan.json) before the [first Norway transfer](norway-ambiguous-counter-ice-tiebreak-first.json). Its one multi-option counter, B69, **abstains**: both `S387` and `S389` have high origin probabilities and visible ice (maximum fractions 0.412 and 0.334). This is the correct behavior for this rule; forcing either choice would hide unresolved identity. The transfer supplies no evidence of generalizable ambiguity resolution.

Ice coverage distinguishes a broadcast close-up from a delivery view in some cases, but it is not a delivered-stone detector. Both competing views may contain ice, a brief delivery may fall between samples, and bright uniforms or graphics may look similar. A high-precision counter-to-event assignment still needs continuous physical motion or another independent cue across camera changes. The result does not improve or measure complete-match physical throw F1.

Re-run the development scan with `PYTHONPATH=prototype feasibility/scripts/python.sh prototype/scripts/audit_2022_ambiguous_counter_ice_tiebreak.py`. The Norway first-run output is preserved; its plan records the frozen inputs and rule.
