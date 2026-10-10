# Third-source gap-screen transfer — 7 October 2026

Source: Slovakia–USA Beijing 2022, `Ns12UZ5nlPk`, full available interval
0–7616 s. Source SHA-256:
`eba1d86944a2f4278b6e5e2c7549d12b47e5e8a51bf0c680b2db372c6ec12420`.
The recording's 1650–2760 s interval was previously inspected for a
counter-adapter coverage probe, but its complete-recording unknown-layout
gaps have not been reviewed for the new visual-gap screen.

Use the unchanged five-minute layout preflight and scan only interior unknown
spans bracketed by Beijing-supported runs. Prepare source-only coarse throw
windows for every such span before opening either raw visual candidates or
scene-screen decisions. Score candidate point timestamps against those windows
one-to-one with zero extra tolerance; report raw and screened TP/FP/FN
separately, preserving all first outputs. The source-only reference is agent
blind but not independent human validation. Opening/closing gaps and incomplete
video coverage remain outside this candidate score.

Frozen code SHA-256 before gap preflight/source inspection:

- `prototype/gap_motion_candidates.py`: `24ff5cb8b972b280fec5fda629cceb98466ff08609a488aec1dc4406361d2500`
- `prototype/stone_motion_fallback.py`: `c6ebacf8c46e50b08f5ab02ee4a206fec6e247d35393ad7439be3b21bf4a3522`
- `prototype/scripts/scan_beijing_layout_gaps.py`: `570b7f9969b2940ba3d51cbc3d0df91492c814a0b3ff6856a834ea51`
- `prototype/gap_scene_confirmation.py`: `e55a108f671b52ad3558e52676ef523f46e2f4f3cecfc986853f21df73ca57f2`
- `prototype/scripts/screen_gap_motion.py`: `b56225469bf19f0cd6ecd7feb1bfa739d662315576d40dca23f9c4ad04861d67`
- `prototype/layout_preflight.py`: `b6917e5066a3c01480cc69db16a03dfc149484f8e087f354e68fc62a90d54a2d`
- `prototype/throw_event_benchmark.py`: `f5a76cc3ea8b37ff13d90fc919f7192753276873b603ef01d4ef5b6f743307f6`

Preflight found three interior gaps: 900–1200, 3900–4200, and 6000–6300 s.
Source-only five-second sheets were inspected across all three, with denser
two-second sheets around the uncertain G03 delivery sequence. Before scanner
inference, seven coarse delivered-stone windows were frozen in three files.
The already-moving red stones at the beginnings of G01 and G03 have uncertain
in-gap delivery onset; those boundary portions are excluded from this score.

- `blind-gap-g01.json` (scored 925–1200 s), SHA-256 `19ceec665a8f701f7e07df24d5139987b61e5d4728683e3d3c2e097ed1f7df4b`
- `blind-gap-g02.json` (scored 3900–4200 s), SHA-256 `62f76d482e340d0d2a126cd97ab50f186407e825df210c98ac8d1160e7cb94b1`
- `blind-gap-g03.json` (scored 6030–6300 s), SHA-256 `4f8654afb748c2a7e37657413476208bfa8a8149019db2f959e342fb0e90f223`
- Source-only sheet manifests `g01`, `g02`, `g03` SHA-256:
  `bc62421637607164415a566312f397968066e7b62a5df6230e77ecdd3c88c487`,
  `35f0ceba93fadd6c071b75c307eecefd453b4da7680436d0b8f0cc72a29755f3`,
  `898b7964595ef36cd87e1d9dc177f4fc500b140a1f0954e2a4eadfab58bf605e`.

Candidate scoring projects each raw or scene-screened candidate point into
the relevant declared scored interval only; candidates in the excluded
boundary portions are reported but do not count in that interval score.
