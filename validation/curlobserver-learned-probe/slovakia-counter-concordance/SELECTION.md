# Preselected counter/visual concordance span

Before reading either modality's output for this interval, select continuous
Slovakia–USA 2022 video at 2400–2700 s. This differs from earlier learned-gap
development spans G01 (900–1200), G02 (3900–4200) and G03 (6000–6300).
First run the current one-second counter audit; preserve every readable and
unreadable sample. Then run the existing five-hertz learned-box and
multiscale-cap channels and their unchanged screens, fusion, colour and
cross-channel rules. Compare candidate times/colours to stable counter
decrement evidence intervals without changing thresholds. Counter updates
are a weak, delayed broadcast reference, not independent ground-truth
release times, and unreadable spans cannot serve as negative labels.

- Source ID: `Ns12UZ5nlPk`
- Source SHA-256: `eba1d86944a2f4278b6e5e2c7549d12b47e5e8a51bf0c680b2db372c6ec12420`
- Span: `2400–2700 s`
- Counter state model SHA-256: `3503fffc8c266f7ecbf2de1dc847f22bfddd42bb749cc164f1bca472e137f281`
- Counter audit runner SHA-256: `1935ad4072aee3f305bb80400fa25f6c621a43e00e694458ca3c2d473b5d54b5`
- Visual-box model SHA-256: `81421342467a0ab8d93f4e08829e5928eefbf98c655b2f3a436493ec002feb63`
- Visual proposal code SHA-256: `746e6f4e0c7c9c32d698573e9a14230321e6dd3e1789db642206cab44bd78f68`
- Context model SHA-256: `9444fc2e38b0f2b4a2efa9a143aec2e8229ee814c2324a3001b179049e672909`
- Colour model SHA-256: `4c63a338ece0fa2e4b3dc9fe479869141371229f68fb28675499e8299ef3910a`
- Cross-channel model SHA-256: `3409bebb7c6ecad693c1d5ed736d4b884edb8c8f90f0c20ec6688a90700684b9`

First preserved result: counter visible 293/300 seconds, six stable red/yellow
decrements, no unresolved changes. The learned-box channel produced 62 raw
tracks; the final screen retained seven candidates. A one-to-one comparison
with the pre-frozen ±15 s weak counter windows matched all six temporally,
five with matching colour, and left one red cap candidate unmatched. The
original coarse-window scorer rejected the overlapping proxy windows, so a
dedicated maximum one-to-one concordance scorer was added; this is a scorer
compatibility change, not a threshold adjustment. The score is stored in
`frozen-first-concordance-score.json` and **is not event F1**.

Postscore source sheets show a yellow delivery near 2480 s while a red stone
also moves near the house. The fitted colour-refinement rule incorrectly
changed the accepted yellow track to red because that later red track had
more image-space motion. The red cap candidate at 2440 s appears near house
stones after the earlier red delivery; its delivered-versus-displaced identity
is not proven, but the counter has no second red decrement there. This is a
concrete failure of using strongest motion as throw identity. Do not promote
this visual fallback to confirmed event output on this evidence.

A **postscore camera-relative motion probe** then estimated affine camera
movement from tracked image features and measured each candidate's residual
motion relative to the rink. It retained registration failures and required
at least 30 inliers and a 0.25 inlier fraction before reporting a motion
sample. Of eight selected tracks, the accepted red house track `G01-R11`
had zero reliable >5 px relative-motion pairs, while the delivered yellow
`G01-Y04` had three consecutive such pairs. The extra cap track `G01-R05`
had only two consecutive pairs despite a long 19.6 s screen track; source
frames at 2440–2445 s show the camera tilting over stationary house stones.
However, the red-shirt track `G01-R03` also had three consecutive relative
motion pairs, so camera compensation alone is not a stone or throw detector.
The frozen measurement and all pair-level registration data are in
`postscore-camera-relative-probe.json`. No event decision was changed.

A further exploratory gray-body fraction immediately below eight selected
candidate boxes did not separate shirt/stone reliably: learned boxes often
cover the whole stone rather than just its handle, and ice or wheelchair
details occupy the sampled region. For example, the true yellow `G01-Y04`
returned roughly 0.12–0.38 neutral fraction across five sampled points,
overlapping the false red-shirt `G01-R03` after its first frame (roughly
0.19–0.44). This handcrafted appearance cue was not implemented as a gate.
