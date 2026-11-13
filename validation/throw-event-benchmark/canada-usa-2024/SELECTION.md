# Pre-inference same-production transfer — 7 October 2026

Source: 2024 wheelchair championship Canada–USA, catalogue row 230,
https://www.youtube.com/watch?v=Z1yEOv__bDc. Selected before source download,
inspection or candidate inference. Fixed interval: 1650–2760 s, if available.

Downloaded source duration: 8633.1333 s. Source SHA-256:
`18f4fe4ac910e2da7e1ed453ade9d291363ab7e01f8d0d207634a3d589efe0da`.
The source-only coarse reference was completed before candidate inference:
`blind-reference.json` SHA-256
`43a803fbe305b562202ab4fcdbbc2bf96ffc84be047d617956b328a0d1d1b924`.

This checks an experimental candidate developed after three exposed 2024
recordings. It does not validate a complete match or another camera family.
Create a source-only coarse reference and freeze its hash before inference; if
the stills cannot support even a bounded reference, state that before inference
and report only coverage. Preserve the first predictions and score.

Frozen rule: track coloured/neutral-body observations in the normalized 2024
left-panel early ROI; emit after a 24-px, six-observation, monotonic motion span
in either y direction without requiring a fixed line. Measure grayscale pixel
change between frames 0.25 s before and after the observed track midpoint.
Confirm x within 160±60, changed pixels in an 80×80 neighborhood ≤1250, and
retain only the earliest same-colour/same-direction passage within 10 s and
30 x-pixels. All rejected candidates remain in evidence. The 1250 threshold
was selected after inspecting the three development scores; their combined
52/0/0 is **in-sample fitting**, not validation.

Frozen code SHA-256:

- `prototype/throw_detection.py`: `40678c23b117f527c80375ff7d7fbe3a1119fb94c4650b05698cd2c76be9628f`
- `prototype/span_passage_detection.py`: `45a14f710e6523f1036f939b90fb196c0c6e7a636c47ab443000eb20340d42e4`
- `prototype/passage_motion_context.py`: `cb5d4a6a0a14899579f69f11028b399fe719b4246760fd7aef25a7b27d35567c`
- `prototype/span_context_confirmation.py`: `f53813d594ed2f820c14d5dac79a4490234e99c3dff28c267ded99b7541f704c`
- `prototype/scripts/run_span_probe.py`: `35f3062165aac099e9b9337fbd7614f98e865c248774872ef89c2034b03b8653`
- `prototype/scripts/measure_passage_motion_context.py`: `50e9a1a9b907cffa89bf314eb8defab2cfd5f4011c3a94214011dbf84d45935c`
- `prototype/scripts/confirm_span_context.py`: `44ccc5d1fc494acaf7f0eadb09f4d9b3eb1349ee1a1492e8baf01cb244a2451b`
- `prototype/throw_event_benchmark.py`: `f5a76cc3ea8b37ff13d90fc919f7192753276873b603ef01d4ef5b6f743307f6`
