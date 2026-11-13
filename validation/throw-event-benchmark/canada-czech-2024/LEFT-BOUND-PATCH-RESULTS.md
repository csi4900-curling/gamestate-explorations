# Frozen appearance screen on extended-bound paths

The wider left-view proposal bound recovered source-visible stone paths for
Canada–Czechia S41 and Canada–Italy S03, and earlier coverage for
Canada–Scotland S02. To test the *next* stage, the isolated
[patch runner](../../../prototype/scripts/score_left_bound_path_patch.py)
uses the exact [frozen cross-match stone-patch model](../../curlobserver-learned-probe/cap-patch-crossmatch-v1/model-excluding-china-dev.npz)
whose SHA-256 is recorded in the original [full-match patch audit](full-match-patch-postscore.json):
`10036a8b13e7e35f0be3cfd7280e9e0afaa3cf5b5da6cecc5623fb79695e0670`.
It samples the first, middle, and last observation of each selected path,
scores the same cap crop and calls the unchanged `screen_candidate` rule.
The proposal bound changes; the model and decision rule do not.

| Candidate | Source review | Positive patches | Isolated two-cue result |
| --- | --- | ---: | --- |
| [Czechia S41](gap-review/s41-extended-patch-postscore.json) | [Moving red stone](gap-review/s41-left-bound-path-frames/s41-path-review.jpg) | 3/3 | provisional support |
| [Italy S03](../canada-italy/left-bound-full-interval/s03-extended-patch.json) | [Moving yellow stone](../canada-italy/left-bound-full-interval/s03-source-review/s03-path-review.jpg) | 2/3 | provisional support |
| [Scotland S02](../canada-scotland-2024/left-bound-full-interval/s02-extended-patch.json) | [Moving yellow stone](../canada-scotland-2024/left-bound-full-interval/s02-source-review/s02-path-review.jpg) | 3/3 | provisional support |
| [Czechia S96](gap-review/s96-extended-patch-postscore.json) | [Player/footrest path](accepted-low-score-source-review/s96-path-review.jpg) | 0/3 | rejected in this isolated replay |
| [Czechia S143](gap-review/s143-extended-patch-postscore.json) | [Postgame movement](source-review/s143-6374.7.jpg) | 1/3 | **false path still provisionally supported** |

This is a useful positive result for S41 and S03 at the motion-plus-appearance
stage, but **not a precision or recall measurement**. It checks five
source-selected candidate paths, omits cross-candidate deduplication and
complete recording scans, and does not independently verify throw identity.
S143 shows that one positive patch remains an unsafe event identity test.
The frozen full-match screen still contains S143 and abstains on S41; this
development replay has not replaced it. Scotland S02 was already accepted by
its existing later-stage screen. Italy S03 was accepted by a separate
shared-prefix development screen, while its frozen repair screen abstained.

For provenance, the first exploratory pass accidentally used a different
side-view model; its five JSON results are retained with
`alternate-sideview-model` in the filenames. **They are not the results in
the table.** Each table artifact records the model and code hashes. The
different model's rejection of visible stones reinforces that model choice
must be fixed and verified before any comparison.
