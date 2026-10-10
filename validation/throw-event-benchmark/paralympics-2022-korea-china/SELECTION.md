# Frozen Korea–China 2022 full-match transfer selection

Selected before any local video frames or detector predictions were inspected.
This is **not** the separately reserved 2025 Wetzikon evaluation source.

- Replay: [Paralympic Games, Korea vs China, Beijing 2022 round robin Day 3](https://www.youtube.com/watch?v=ia3HIF_4Bdo), ID `ia3HIF_4Bdo`. Publisher metadata queried on 8 October 2026 reports duration 6,830 s.
- Independent order source: [official Beijing 2022 results book](https://curlit.com/PDF/PWG2022_ResultsBook.pdf), local SHA-256 `61817ee1db60ab74884c6c5fae6f870259ccc7c01b7e904b411dcaa8dff32e23`, PDF page 393 game result and pages 394–399 shot by shot, game code `PREL000702`. Before detector inference, the existing PDF parser counted 16 numbered shots on each of six pages, **96 published deliveries**, with KOR red and CHN yellow. The pages provide shot order and diagrams but no video release times.
- Frozen source-only pipeline runner: `prototype/scripts/run_full_shot_evidence.py`, SHA-256 `b622a65c1d2104fef4bae86d6adce6d4e571ede2a2c2bdba147ef813b73925ed`.
- Frozen shot-origin model: `validation/curlobserver-learned-probe/shot-origin-pair-v1/model-excluding-swiss-dev.npz`, SHA-256 `9586973ae7cbc632c65e3b757015f30d1d2fcf38190d50c39bb43c4ed827661a`.
- Frozen stone model: `validation/curlobserver-learned-probe/model-v1/model.npz`, SHA-256 `81421342467a0ab8d93f4e08829e5928eefbf98c655b2f3a436493ec002feb63`.
- Frozen optional held-cap cue and ice check: `prototype/origin_release_passage.py`, SHA-256 `20b4278bb7d9852df0f4da7a9607d4e164a0734c377da45fb444e4e189821976`; `prototype/origin_release_ice_support.py`, SHA-256 `6b05e5f15794439b5c4b106720d54a0bcaf1949ad05efb0cf52b68d07227dd36`.

The 640×360, 30 fps video-only research copy was acquired before inference as `source.mp4`, SHA-256 `b779f017ff450293d13f589e3eb64816b3620fee81081e06c9a4b368e90ccbb9`; `ffprobe` measured duration 6,829.666667 s. Run the unchanged full-source pipeline on integer interval 0–6829 s, retaining the final 0.667 s as a declared unprocessed tail. Report every stage's coverage gaps and abstentions, provisional candidate count, clean broadcast-counter count, counter-to-visual associations, colour conflicts and official shot-count discrepancy. Compare to official shot order only after the source-only predictions are frozen. Any source review or rule change after that first result is development, not a revised untouched score.

This transfer cannot establish throw-event precision, recall or F1: the official PDF has no video timestamps. A complete independent timestamped reference is still required for that claim. Do not interpret one-to-one official-order alignment as physical throw validation.
