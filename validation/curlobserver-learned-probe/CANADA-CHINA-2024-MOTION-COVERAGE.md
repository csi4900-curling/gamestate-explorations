# Canada–China 2024: directional stone-motion coverage

Development audit, 8 October 2026. This tests whether the existing split-view calibration and colour-cap proposer can supply moving-stone evidence in **all 18 source-only coarse delivery windows** of the fixed 1650–2760 s interval. It is a postscore development experiment, not event-detector F1, physical trajectory accuracy, or independent validation.

The [one-second registration audit](canada-china-2024-all-windows-camera-registration-1s-development.json) sampled 533 frames. The left view registered 533/533; the right registered 521/533, with all 12 abstentions in C02–C03. The [stone-proposal audit](canada-china-2024-all-windows-stone-proposals-1s-development.json) produced candidates on 464 left frames and 498 right frames. False proposals on clothing remain possible, so these are not stone-detection precision figures.

The first selector required exactly one proposal of the delivery colour per frame and found a moving run in only **6/18** windows. A second [far-entry selector](../../prototype/stone_proposal_path.py) followed a candidate moving from the far lane toward the house while retaining multiple parked same-colour candidates. It requires sustained forward motion, bounded speed and speed change, and a unique longest path. Where two equally supported paths diverge near other stones, it exports only their common observed prefix. The first three windows play toward the opposite house, so the same directional logic was run in the left receiving view; C03 needed 0.5 s sampling to recover four visible points.

| Evidence from the [combined handoff](canada-china-2024-directional-motion-evidence-development.json) | Windows |
| --- | ---: |
| Provisional unbranched moving phase in the right receiving view | 9 |
| Provisional right-view path ending at identity ambiguity near the house | 6 |
| Provisional moving phase in the left receiving view | 3 |
| No moving-phase evidence in a coarse reference window | 0 |

This is **18/18 windows with some observed moving-stone evidence**, not 18 complete throws. C01–C03 have only 1.5–3 s of left-view observations. Six right-view paths stop at an identity branch, with the first ambiguous frame recorded. Many other paths end at the coarse reference-window boundary while the stone is still moving. The [C04 extended pilot](CANADA-CHINA-2024-CAMERA-TRANSFER.md) separately observes visible stability at 1917.5 s after 56 consecutive half-second proposals; that criterion has not been applied across the match.

The marked-frame review sheets show first, middle, and last selected observations for the [first five](canada-china-2024-all-windows-motion-review-01-development.jpg), [middle five](canada-china-2024-all-windows-motion-review-02-development.jpg), and [last five](canada-china-2024-all-windows-motion-review-03-development.jpg) right-view paths, plus the [three opposite-direction left-view paths](canada-china-2024-left-reverse-motion-review-development.jpg). In these sampled frames the marks sit on visible moving stones, but the same developer inspected the footage and built the selectors. The visual check does not certify identity across all frames, metric accuracy, or recall outside the reference windows.

## Passage-to-motion correspondence diagnostic

A [separate temporal join](../../prototype/motion_correspondence.py) asks whether each passage candidate has exactly one compatible receiving-view path starting within 6 s after its line crossing, with the same colour and expected view direction. Against the **frozen first corridor candidates**, [17 of 21 passages](canada-china-2024-frozen-first-passage-motion-development.json) have such support. The four without it are D03, D05, D11, and D23—the four previously reviewed false candidates—and the previously missed C01 path has no passage to link. For the later, in-sample [confirmed candidate set](canada-china-2024-confirmed-passage-motion-development.json), all 18 passages have one temporal match. Matched first-path delays are 1.32–4.65 s in that set.

This is evidence that receiving-stone motion **could be a useful candidate filter**, not a measured improvement in throw F1. The motion paths were searched *inside known coarse delivery windows* and selected with rules developed after inspecting this match. An unsupported passage outside those windows was never given an equal chance to find a path. A valid filter test must scan motion after **every candidate** without using reference windows, freeze the rule, and score on a new untouched recording with independent labels.

The pipeline still needs to infer play direction and event windows from the video itself, continue through cutaways and interactions, associate the delivered stone with a settled board, and calibrate stone footprint positions independently. The reserved unseen end remains untouched. None of these paths is marked simulation-ready, and no score or complete game state is inferred.

A later [candidate-centric filter audit](CANADA-CHINA-2024-CANDIDATE-FILTER.md) removes the reference-window shortcut from the receiving-motion scan. It exposes a red-jersey false track and tests a second appearance cue; all resulting numbers remain in-sample development diagnostics.
