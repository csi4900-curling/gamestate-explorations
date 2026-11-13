# Frozen next-recording probe: Canada–Latvia 2024 RR8

Recorded before downloading or inspecting this match for this probe. Source is project catalogue row 232, YouTube ID `YCfdKLu-BRc`. It was not found in existing project analyses. Keep the reserved Canada–USA match excluded.

Test the **1650–2760 s** interval if the source contains it; otherwise record that the interval is unavailable and do not move the window after viewing. Produce a 360p full-match copy and an aligned 1080p interval copy, with hashes and six fixed alignment checkpoints. Before inference, make fixed 5 s source-only full/left/right contact sheets; do not use detector output to select them. An exhaustive physical-throw reference is not available. Report candidate coverage and abstentions, **not precision, recall, or F1**, unless an independently labelled source-only reference is frozen before inference.

Run the unchanged 10 Hz line-independent span detector and x = 160 ± 60 px corridor. Preserve raw and corridor candidates. On the 1080p interval, select the right-camera local reference by sampling 1655, 1665, …, 2755 s. Accept only the existing registration gate at 160 px maximum corner displacement. Greedily group accepted frames in time order when every member is within 40 px maximum projected-corner distance of the new frame; choose the largest group (earliest group breaks ties), then its frame with most inliers (lower RMSE and earlier time break ties). If no anchor is selected, abstain from the rebased branch; do not hand-pick one. Keep the original left-camera reference.

Use that selected anchor in every right-camera stage: 0.5 s candidate-centric motion sampling with the original clean background and transported camera prior; same-shot registration hold with the existing ice-similarity gate and maximum 10 s anchor gap; bounded-gap selection with a 4.1 s maximum; three-point frozen patch model; timed-path duplicate check; and the existing two-cue screen. Preserve each stage and its input hashes. Do not change thresholds, candidate IDs, patch model, or source interval after seeing results. A rejected frame remains an abstention unless the frozen hold rule accepts it.

This protocol was designed after exposure to Canada–Scotland; Canada–Latvia is the next transfer test. Registration rates and provisional candidate counts remain diagnostic, not event accuracy. If the selected anchor registers poorly or the screen fails, preserve those failures and diagnose only afterward in a separately marked development branch.

Frozen SHA-256 values at plan time:

| Component | SHA-256 |
| --- | --- |
| Span runner | `35f3062165aac099e9b9337fbd7614f98e865c248774872ef89c2034b03b8653` |
| Corridor runner / model | `d73c529bd32a8e68b45cc05021be2d0d68e50fed22bd8305c2fc29032b5f1002` / `3f8829d965d8a62312d9016e6955d1cc2c8546ad4e19c47b2d3c7a934f5bd036` |
| Fixed-grid selector | `9f0d95475b6913a17dec9ed9a23c1b66a24e4f5b75a4ce0af2061bdd5215489d` |
| Candidate-centric scan / rebase core | `2b2084161cab0c0671197623c5c9ae1b9322d9f0b0662cdcdbcc59b9e59e084c` / `6d917ae47e3dfaef45ab5def54f4c5b5ea15c3e82f3d79181e3ac17900904ff9` |
| Registration hold / bounded-gap selection | `b3dd5ca3e64b4ed46b8ea618e7ca1895debc661e741843b42e0082a50b5d24a3` / `45ecb222ef75899326febfbae8a0e1c6aed5d3ffad04bf60408787e22a891b8c` |
| Gap-path patch runner / frozen patch model | `49320497b85df99e0712f7f62fce17cb88c9130bc83f3edcaed7b98cb04a7ef6` / `10036a8b13e7e35f0be3cfd7280e9e0afaa3cf5b5da6cecc5623fb79695e0670` |
| Timed-path dedup / final screen | `2f05c912ecb0ee0a434ef128f86cd04d7ae90416845d840f4148c856bb1d25a0` / `94c981a02b8c9ade9ebeea9e49baf6b144e9a9f59ab8d3de69ea49f0afeb5cfd` |

## Source-only checkpoint before inference

The source is available for the fixed interval. The full 360p copy is 640 × 360 at 30 fps, duration 7059.067 s, SHA-256 `a7431b68ba6fb0df407383973a525a01eadbee2490caa0438a5a11d2df1dba13`. The 1080p interval copy is 1920 × 1080 at 30 fps, duration 1110.033 s, SHA-256 `780186549f4330f0e381d533af9815d21525495ae53db8a4c48048d3d9d8347e`. The [six-checkpoint alignment audit](../throw-event-benchmark/canada-latvia-2024/highres-alignment-frozen-first.json) finds zero best time adjustment at 1750, 1900, 2100, 2300, 2500, and 2700 s; artifact SHA-256 `53bb77f29d82c4f65c68382a685e57059c7622175d04fdd76c132a56bd13495c`.

The fixed source-only [full](../throw-event-benchmark/canada-latvia-2024/source-only-5s-sheets/manifest.json), [left](../throw-event-benchmark/canada-latvia-2024/source-only-left-5s-sheets/manifest.json), and [right](../throw-event-benchmark/canada-latvia-2024/source-only-right-5s-sheets/manifest.json) sheets each contain 222 timestamps, before any detector inference. Their manifest hashes are `899b7a3bd0125c7ba0cda136fc31a5daaf761693ac53d58dbb7fb347f0e02788`, `222a112b22d0abf9063440b0fdbb3e6ad9e5bf9215d859c649738c83994c857a`, and `cb599e64fda6edde74a87edc214bb9556e708ab33e605f795eeeb7972a328492`. No exhaustive source-only physical-throw reference was made from these stills; do not claim precision, recall, or F1 from them.
