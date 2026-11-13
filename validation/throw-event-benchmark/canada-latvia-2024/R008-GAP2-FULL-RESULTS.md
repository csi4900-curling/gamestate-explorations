# R008: a one-second association miss and full gap-two tradeoff

The older right-entry review candidate **R008** has [source-visible moving red stone pixels](../layout-router/full-2024-coverage/latvia24-full-v1/right-entry-review/sheet-01.jpg) at 5115–5122 s, while the frozen full right area-aware scan emitted no corresponding directional proposal. The [exact-point audit](r008-area-gap2-split-audit.json) identifies the failure: its six saved prefix observations were divided between full-scan raw tracks **A352** (5115–5118 s) and **A353** (5120–5121 s). Their combined points equal the older R008 prefix exactly. The existing two-second-gap area linker and the separate global-assignment linker each reconnect those same six points in a [local replay](right-area-gap2-r008-5080-5140-development.json) ([global replay](right-global-r008-5080-5140-development.json)). Their passage timestamp, 5116.556 s, is a halfway observed-motion-span cue, not a physical release time. The older 5119.918 s timestamp comes from a different image-line rule.

The same two-second-gap rule was then run **unchanged** over the entire 0–7058 s Latvia source. The [full result](full-right-area-gap2-development.json) emits **555 raw tracks and 118 directional review proposals**, versus **485 tracks and 100 proposals** for the one-second-gap version. Full-scan path A398 contains the exact six R008 observations. This is a recovered source-visible path, not a measured improvement in physical throw recall.

Using a fixed comparison of same colour, same image direction, and passage times within eight seconds, **15 gap-two proposals have no one-second-gap counterpart**. Every one appears in the [source packet](full-right-gap2-novel-source-packet/manifest.json). The [same-agent source review](full-right-gap2-novel-source-audit.json) classifies their sampled prefix pixels as follows:

| Source-pixel class | Count | Examples |
| --- | ---: | --- |
| Moving stone body in sampled prefix | 3 | A176, A388, A398 (R008) |
| Person or equipment | 6 | A046, A156, A303, A353, A431, A553 |
| Mixed objects or uncertain track identity | 6 | A244, A282, A312, A437, A481, A518 |

A176 occurs 6.9 s from the accepted left red crossing S59, and A388 occurs 9.8 s from accepted left red S110. That timing suggests possible cross-view correspondence but does not verify same-stone identity. A398 is the recovered R008 path. The single old directional proposal without a gap-two counterpart is old **A046** at 987.69 s, previously source-reviewed on person/clothing pixels. Gross proposal counts also include changed or additional paths near old proposal times; they cannot be read as a throw gain or loss.

The result argues for a **recall-oriented, multi-association review tier**: the wider gap recovers R008, but it also admits people and identity splices. The [152-candidate handoff with R008 source review](full-match-area-censored-candidate-handoff-r008-source-reviewed-development.json) keeps the physical-throw count unknown, 98 possible-event review proposals, and every simulation-readiness flag false. The gap-two scan is preserved as a separate diagnostic; it has not replaced the frozen one-second scan in the event ledger. Independent source-first full-match labels and verified same-stone view transitions remain necessary before choosing an association rule by precision/recall/F1.
