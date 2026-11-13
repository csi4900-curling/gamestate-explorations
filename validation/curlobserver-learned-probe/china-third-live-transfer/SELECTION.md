# Frozen colour-rule transfer over an end transition

The first two China live intervals have been exposed to model development.
This 900–1200 s interval was instead inspected from fixed five-second
source-only sheets, and five coarse delivery windows were frozen before any
detector candidate from this interval was read. It spans live play, a first
end break, broadcast graphics, and early second-end play. Run the unchanged
learned-box, large-cap, screen, fusion, and episode-colour rule, preserving
each first output and reporting temporal and colour-aware scores separately.
The reference is agent-authored development evidence, not independent human
validation or a release-time label.

- Source SHA-256: `c5254bb9103e32c6beac74cf269fc7bcec8ce2c2a710a7d4600c7ddb951f160e`
- Source-only sheet manifest SHA-256: `d578600cd3ecb5a866bce27bc64e5ebc574fe77b8d27372f28a0d66293c4a815`
- Frozen reference SHA-256: `ea33e9e2d44d03e2026817b8a5213fa517d62f91bb4edaaaef8a7af3d4d73692`
- Public-box model SHA-256: `81421342467a0ab8d93f4e08829e5928eefbf98c655b2f3a436493ec002feb63`
- Primary proposal code SHA-256: `746e6f4e0c7c9c32d698573e9a14230321e6dd3e1789db642206cab44bd78f68`
- Episode colour model SHA-256: `4c63a338ece0fa2e4b3dc9fe479869141371229f68fb28675499e8299ef3910a`
- Episode colour runner SHA-256: `da136a8f5db2daee807e4fa3d7d7472b59e281c404a6be71d7173cda6f5d798a`
- Fusion runner SHA-256: `ff73b44c53cbf6d256e6b95345d17516ad2070b0c700261da33c29b979b367dd`

The first frozen score was 4 TP / 0 FP / 1 FN, colour-aware identical, for
F1 0.889. The missed source-only window was CH-T03, red 990–1020 s. Both
learned-box and colour-cap raw tracks followed the red stone around 1003 s,
but the learned track failed its local-ice threshold and the cap track missed
its smooth-motion threshold. A subsequent fitted two-channel pair rule added
that candidate and scored 5/0/0 only **retrospectively** on this interval.
`frozen-first-colour-refined-score.json` and `postscore-paired-score.json`
preserve the distinct results.
