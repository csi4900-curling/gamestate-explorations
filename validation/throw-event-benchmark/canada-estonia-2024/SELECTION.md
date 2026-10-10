# Pre-inference same-production candidate transfer — 7 October 2026

Source: 2024 wheelchair championship Canada–Estonia, catalogue row 229,
https://www.youtube.com/watch?v=PXGfMeiTKMA. Selected before downloading,
viewing or running the candidate. Fixed interval: 1650–2760 seconds, subject
to source duration; if it is shorter, document the change before inference.

This is an untouched **same-production** transfer check of the experimental
2024 split-screen candidate. It does not validate the Beijing camera adapter
or complete-match F1. Prepare source-only coarse delivery windows and freeze
their hash before inference. If the source-only review cannot establish an
exhaustive reference, record that before inference and treat results as a
coverage probe without an F1 claim. Preserve first predictions and score.

Frozen candidate: two departure lines y=60 and y=80, same-direction/same-colour
fusion within 4 s and 20 px; center corridor x=160±60; `confirm_passages` default
speed, competition and isolated-direction rules. These thresholds were chosen
after reviewing Canada–China and Canada–Italy and yielded in-sample 18/0/0 and
17/0/0 interval scores, respectively. No further parameter changes may be
called a first-pass result here.

Code fingerprints at selection:

- `prototype/throw_detection.py`: `40678c23b117f527c80375ff7d7fbe3a1119fb94c4650b05698cd2c76be9628f`
- `prototype/bidirectional_detection.py`: `eb83336a159e04f8deb3fe053f698d90cf22c5cbd549a4a28ea455255a99d293`
- `prototype/passage_corridor.py`: `3f8829d965d8a62312d9016e6955d1cc2c8546ad4e19c47b2d3c7a934f5bd036`
- `prototype/passage_confirmation.py`: `45d047c9d5d3ea72be6d319da43eface518b48b4cb2683120653339533fa2bc7`
- `prototype/scripts/run_bidirectional_probe.py`: `6e9dc9bcaa0952db52627229c11690287a53f8e3b5e78e789fcdcdedfc2d4bc2`
- `prototype/scripts/screen_corridor.py`: `d73c529bd32a8e68b45cc05021be2d0d68e50fed22bd8305c2fc29032b5f1002`
- `prototype/scripts/confirm_passage_candidates.py`: `18509aa5a43c1e32a93500c05f386459bba160d18d2f0c8397579acee55f4e7c`
- `prototype/throw_event_benchmark.py`: `f5a76cc3ea8b37ff13d90fc919f7192753276873b603ef01d4ef5b6f743307f6`

Source downloaded without inspecting candidate output. Duration: 8433 s.
Source SHA-256: `2e2b84bb2d9dffa497ee850ddbeaf0d5cae0d697377b6eee6a1ef481f449f3da`.
Source-only 5-second full and left-panel sheets were reviewed before inference.
The 17 coarse delivery windows in `blind-reference.json` were frozen before
inference; SHA-256: `d53b1a878c03134c328e83f0317c946c909e0c83d4395fb8a7d9c1433cc5c7fa`.
The reference cannot certify continuous-video exhaustiveness, as declared in
the JSON. It remains useful as a bounded first-pass transfer check, with that
measurement limitation stated beside any score.
