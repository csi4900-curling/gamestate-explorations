# Frozen Canada–Norway 2022 transfer plan

Source: [official Paralympics full-match replay](https://www.youtube.com/watch?v=EoSwgOcH71g), 640×360, 30 fps, duration 9039.203 s. Local `source.mp4` SHA-256:
`c49fb90959c13b690447dccb87a0b78e0bba8537aa961339a92f934226baf2b3`.
This source was first acquired on 7 October 2026 after development on the
other three Beijing 2022 recordings. It is not the reserved Wetzikon source.

The [official Beijing 2022 results book](https://curlit.com/PDF/PWG2022_ResultsBook.pdf)
identifies Canada–Norway as `PREL001501`, result page 129 and shot pages
130–137. The eight ends each contain 16 numbered shots, 128 total. These
published pages give shot order and post-shot diagrams, not video times.

Before running inference, freeze:

- Shot-origin model `validation/curlobserver-learned-probe/shot-origin-pair-v1/model-excluding-swiss-dev.npz`, SHA-256 `9586973ae7cbc632c65e3b757015f30d1d2fcf38190d50c39bb43c4ed827661a`.
- CurlObserver stone model `validation/curlobserver-learned-probe/model-v1/model.npz`, SHA-256 `81421342467a0ab8d93f4e08829e5928eefbf98c655b2f3a436493ec002feb63`.
- Full-source runner `prototype/scripts/run_full_shot_evidence.py`, SHA-256 `b622a65c1d2104fef4bae86d6adce6d4e571ede2a2c2bdba147ef813b73925ed`.
- Held-cap origin release cue `prototype/origin_release_passage.py`, SHA-256 `20b4278bb7d9852df0f4da7a9607d4e164a0734c377da45fb444e4e189821976`.
- Below-cap ice gate `prototype/origin_release_ice_support.py`, SHA-256 `6b05e5f15794439b5c4b106720d54a0bcaf1949ad05efb0cf52b68d07227dd36`.

Run the unchanged full-source evidence pipeline on 0–9039 s. Then apply the
frozen held-cap and ice rules to every origin-positive but cap-unconfirmed
shot window. Compare visual-only candidates with clean, colour-concordant
broadcast counter updates under the existing monotone counter-proxy rule.
Extract the official game ledger independently from the PDF. Report full-game
candidate count versus 128 official deliveries, per-end coverage, counter
readability, visual-only proxy matches and all abstentions/conflicts. Preserve
first results before any source review or rule changes.

The counter is a delayed weak proxy. The official pages lack release
timestamps. This transfer can reveal coverage and false-positive problems,
but it cannot certify complete-recording physical throw precision/recall/F1
without an exhaustive independent timestamped reference.
