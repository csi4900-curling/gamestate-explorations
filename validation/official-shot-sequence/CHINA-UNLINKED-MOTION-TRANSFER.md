# China transfer of the Norway unlinked-motion proposal rule

The [Canada–China source-wide catalog](china-global-shot-scoped-cap-motion-first.json)
applies the same narrow 1 Hz red/yellow cap rule within the saved 630 camera
shots over the full 8,356-second recording. It finds **160 motion tracks**.
The [candidate graph](china-global-cap-motion-candidate-links-first.json)
uses the frozen 129-candidate China development ledger and the same
`floor(start)-5` to `ceil(end)+15` search expansion used on Norway. It has
122 possible track-to-candidate links and 39 unlinked tracks. These are
source-motion observations, not physical throw counts.

Without changing the Norway thresholds, the
[adjacent-origin rule](china-unlinked-motion-rescue-transfer-first.json)
returns **six review proposals**. Every origin shot is absent from this
129-candidate ledger; none is automatically added. The rule was selected
after reviewing Norway, so this transfer probes selectivity on a second
recording but is not independently labelled precision or recall.

| Origin → receiving track | Source-frame interpretation |
|---|---|
| S108 → S109-R01 | A China delivery view precedes red travel; the exact delivered-stone link remains unverified. |
| S216 → S217-R01 | Red delivery and receiving travel are compatible. S216 was already captured by a separate source-rescue workflow in the later provisional event union. |
| S320 → S321-R01 | A China delivery view precedes red travel; the delivery stone is partly obscured. |
| S357 → S358-Y01 | A Canada player is seen with a yellow stone before yellow travel. |
| S377 → S378-R01 | **Colour mismatch:** the delivery view shows a yellow stone, while the unlinked receiving track is red. It may be an existing red stone moved by a yellow delivery. This proposal must not be used to infer a red throw. |
| S449 → S450-R01 | A China player is seen with a red stone before red travel. |

The timestamped source frames are in [part 1](china-unlinked-motion-transfer-source-frames-1.jpg)
and [part 2](china-unlinked-motion-transfer-source-frames-2.jpg). This is
agent-authored development review, not independent physical-event labelling.
The S377 case exposes the missing filter: a receiving-view moving stone can
have a different identity and colour from the delivered stone after a
collision or cut. A robust event proposal needs source-local release-colour
evidence and a separate cross-view identity hypothesis, with abstention when
that link is unresolved.

Reproduce the full catalog and transfer with:

```sh
feasibility/scripts/python.sh prototype/scripts/build_china_global_cap_motion_catalog.py
feasibility/scripts/python.sh prototype/scripts/transfer_unlinked_motion_rescue_to_china.py
feasibility/scripts/python.sh prototype/scripts/render_china_unlinked_motion_transfer_frames.py
```

The saved outputs include source/code hashes and refuse to overwrite their
first runs. The China and Norway candidate ledgers remain unchanged; these
proposals are not F1 scores or simulation-ready events.

The [release-side colour audit](UNLINKED-MOTION-RELEASE-COLOUR.md) finds a
unique red cue only for S216 among these six China proposals. It abstains on
S377, so that receiving red motion cannot be used to recolour the visibly
yellow delivery.
