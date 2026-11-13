# Pre-inference same-family transfer check — 7 October 2026

Source: 2024 wheelchair championship Canada–China, catalogue row 228,
https://www.youtube.com/watch?v=Y_U6gzqORUs. Selected before download or source
inspection. Fixed media interval: 1650–2760 seconds.

Prepare source-only coarse delivery windows and freeze them before reading any
candidate output. Keep the first score unchanged. Do not request user labels.
This is a same-production test of a geometry selected after viewing the
Canada–Italy match, not cross-family or independent human validation.

Frozen candidate and scorer fingerprints:

- `prototype/throw_detection.py`: `40678c23b117f527c80375ff7d7fbe3a1119fb94c4650b05698cd2c76be9628f`
- `prototype/bidirectional_detection.py`: `eb83336a159e04f8deb3fe053f698d90cf22c5cbd549a4a28ea455255a99d293`
- `prototype/passage_corridor.py`: `3f8829d965d8a62312d9016e6955d1cc2c8546ad4e19c47b2d3c7a934f5bd036`
- `prototype/scripts/run_bidirectional_probe.py`: `fb943230e3f820b2f0373329e159af4617c220dcccc6f65369bb80d61123ad26`
- `prototype/scripts/screen_corridor.py`: `d73c529bd32a8e68b45cc05021be2d0d68e50fed22bd8305c2fc29032b5f1002`
- `prototype/throw_event_benchmark.py`: `f5a76cc3ea8b37ff13d90fc919f7192753276873b603ef01d4ef5b6f743307f6`

Screen with normalized left-panel center x=160 pixels, half-width=60 pixels.
Score both raw and screened candidates with zero extra temporal tolerance.

Source SHA-256: `2a0885f28b5496670f99ab159c37aeb270cc454e65b909ce8a37a0398f7771ac`.
Source-only reference frozen before inference as `blind-reference.json`, SHA-256
`28d6c004248c4ccc61e081f459d83f0e260d3c9dcad6cd360fdb09258fad068e`.
