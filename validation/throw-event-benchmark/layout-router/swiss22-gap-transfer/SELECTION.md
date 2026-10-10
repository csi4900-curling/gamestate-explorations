# Pre-inference visual-gap transfer selection — 7 October 2026

Source: Sweden–Switzerland Beijing 2022, `ZJAMdkERdpE`, complete available
interval 0–7734 s. Source SHA-256:
`49429abdd3796e8240e66c201d37e94e71a7bb6225890b2492bea26d2f70d560`.
The 1650–2760 s section was previously used to develop the Beijing counter
adapter, so this is **not an untouched whole-recording event test**. The
full-recording unknown-layout gaps have not yet been source-reviewed or run
through the visual-gap scanner.

Protocol: run unchanged five-minute layout preflight over the full interval.
For each *interior* unknown gap bracketed by Beijing-supported runs, create
source-only coarse delivery notes before opening visual gap-scan predictions.
Then run the unchanged scanner. Report candidate-to-window TP/FP/FN with
explicit uncertainty about sparse source sampling and any camera cuts. Keep
the first scanner output and score. Opening/closing gaps are outside this
scanner's declared scope and remain coverage gaps.

Frozen code SHA-256:

- `prototype/gap_motion_candidates.py`: `24ff5cb8b972b280fec5fda629cceb98466ff08609a488aec1dc4406361d2500`
- `prototype/stone_motion_fallback.py`: `c6ebacf8c46e50b08f5ab02ee4a206fec6e247d35393ad7439be3b21bf4a3522`
- `prototype/scripts/scan_beijing_layout_gaps.py`: `570b7f9969b2940ba8dc080ba3d51cbc3d0df91492c814a0b3ff6856a834ea51`
- `prototype/layout_preflight.py`: `b6917e5066a3c01480cc69db16a03dfc149484f8e087f354e68fc62a90d54a2d`
- `prototype/scripts/run_throw_pipeline.py`: `dd0c30314988ce91c2216b5423aefef76b52f290409cf86500922bd7d6261aec`
- `prototype/throw_timeline.py`: `9269b7450bee435181b0ef6368c020a27b6973389611f66cf2f0998a25588c8b`

Preflight (before visual-gap inference) found one interior gap, 3900–4200 s.
Source-only 5-second sheets across the full gap and 2-second sheets near the
visible delivery identify one coarse red delivery at 3904–3938 s. The
reference was frozen before visual-gap inference:

- `blind-gap-reference.json` SHA-256: `ad273feef7a359bb13d706414974013d822ba5c2b8df9806eb552cd9173eea8a`
- `source-only-sheets/manifest.json` SHA-256: `2b042b06fca388fa751973028876a59a8dd7413a0379357a9015bd658ebd14e5`
- Scorer `prototype/throw_event_benchmark.py` SHA-256: `f5a76cc3ea8b37ff13d90fc919f7192753276873b603ef01d4ef5b6f743307f6`
- Scorer runner `scripts/score_throw_events.py` SHA-256: `d4f948a24c60b89c795a93112b234374f07ebafd202a41264045147dfc482487`

For scoring, project each visual candidate to its observed first-frame point
and colour inside [3900,4200]; score every candidate one-to-one against the
coarse window with zero extra tolerance. This measures candidate agreement,
not confirmed throw-event F1 or exact release-time accuracy.
