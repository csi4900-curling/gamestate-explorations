# Frozen fifth-recording probe: Canada–Scotland 2024

Recorded 8 October 2026 before downloading or inspecting this recording in this probe. Source: project catalogue row 231, WWhCC2024 Canada–Scotland round robin 7, `https://www.youtube.com/watch?v=mKtmFW-B5UI`. The available source metadata reports a 7347 s recording. Fix the test interval at **1650–2760 s**, matching the prior same-production probes. The reserved Canada–USA recording is excluded.

Run the unchanged line-independent 10 Hz span detector and x=160±60 px left-panel corridor on a 360p full-match copy. Preserve raw and corridor candidates. Obtain a separate 1080p interval copy and verify its source-time alignment against 360p before receiving-camera inference. Then use the existing 0.5 s candidate-centric receiving scan, 160 px registration limit, still-camera hold, bounded-gap selection, conditional dropout rescue, frozen stone-patch model, and screen. Finally apply the newly defined **original-prefix fallback** only to screen abstentions, with five prefix samples, prefix fraction ≥0.7, conditional travel ≥2 m, and at least two accepted patches among three scored prefix patches. A fallback output remains a proposal; do not silently add it to the accepted event count.

This tests whether the S02 failure-mode rule produces bounded proposals on another recording **without changing thresholds after seeing the output**. It does not by itself establish event precision, recall, or F1. If a source-only coarse reference can be made before inference, freeze its file hash first and report coarse agreement separately from independent human validation. Otherwise report candidate coverage and abstentions only. Preserve first-pass artifacts even if they fail.

Frozen code SHA-256:

| Stage | SHA-256 |
| --- | --- |
| Span runner | `35f3062165aac099e9b9337fbd7614f98e865c248774872ef89c2034b03b8653` |
| Corridor runner / model | `d73c529bd32a8e68b45cc05021be2d0d68e50fed22bd8305c2fc29032b5f1002` / `3f8829d965d8a62312d9016e6955d1cc2c8546ad4e19c47b2d3c7a934f5bd036` |
| Candidate-centric runner | `77f9618344b41e773121e0348215206ecb7b6989fe7239f840e120428f612714` |
| Registration hold / bounded gap runners | `10dc284a12da5858c4443339dabd65e53e197a9bd9a96df7208931e23542cc32` / `45ecb222ef75899326febfbae8a0e1c6aed5d3ffad04bf60408787e22a891b8c` |
| Conditional rescue runner / core | `1b97fac7cf14a74307fefbd0e029e3b2be10b1023a55e8a8607c7eeb4b99d494` / `1e893842e9e57fa0e709cd5fddc375013f722f0fff7a20c7ccea26cbdc532918` |
| Patch runner / frozen model | `716ae811e64566044b729883cb051bd757a8a1a8e7f5564b76b08ea72ae1c17d` / `10036a8b13e7e35f0be3cfd7280e9e0afaa3cf5b5da6cecc5623fb79695e0670` |
| Screen runner / core | `ca5fe4e2c34fe3d372be46b0b327a7e2ae412c6885e214e786a5cdb7f6065c8e` / `e8a30d9408f29b4a01253107d09ba64685969aa1b244506fa94b6a6cfd0cd0ae` |
| Prefix fallback runner / core | `948077e3733b8b96008faf4f7969b66e303865394e829be47d709e985a2dc9c5` / `46d3ebd341d4b33c2c8ac0562f0852bebf82dce0b9e4baa471ed3528c07ffa07` |

## Source-only inspection before inference

The 360p HLS copy downloaded successfully: 640×360, 30 fps, 7347 s, SHA-256 `6007ff0d33771aec1aa45f26b5e9271f151e77bcbb6c85a4b613e3aaf3163eae`. Before candidate inference, fixed five-second [full](../throw-event-benchmark/canada-scotland-2024/source-only-5s-sheets/manifest.json), [left](../throw-event-benchmark/canada-scotland-2024/source-only-left-5s-sheets/manifest.json), and [right](../throw-event-benchmark/canada-scotland-2024/source-only-right-5s-sheets/manifest.json) sheets were generated, 222 times each. Manifest SHA-256 values are `5b0a06a95843368e4595dc1df8761b529659228414f83090f0281a6bb047ebd9`, `01a8e68f199f4f36bca6e706ab212ef95cc160ce1618b6c0c17ede67a47fecab`, and `9f8684001e015aab6909dc796eead792ab3853b377a085132e372d0b7d7b7e43` respectively.

These stills reveal many moving stones but do not reliably distinguish every delivery from stone handling and end transitions. **No exhaustive source-only event reference is frozen.** The forthcoming first pass may report coverage and source counterexamples, but no event precision, recall, or F1 for this recording.
