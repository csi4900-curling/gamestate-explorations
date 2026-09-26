# Stone-position accuracy benchmark

Open **http://127.0.0.1:8765/stone-accuracy/** to inspect the images, detections, reference positions and every error.

## Result

The current automatic colour-cap baseline does not pass this benchmark.

| Primary evaluation | Overhead | Oblique | Combined |
|---|---:|---:|---:|
| Frames | 8 | 1 | 9 |
| Visible labelled house-stone observations | 44 | 4 | 48 |
| Detected | 0 | 4 | 4 |
| Missed | 44 | 0 | 44 |
| Unmatched house-region proposals | 4 | 0 | 4 |
| Detection recall | 0% | 100% | 8.3% |
| Position RMSE among matched stones | Unavailable | 54.60 cm | 54.60 cm, only 4 matches |
| Median matched position discrepancy | Unavailable | 53.98 cm | 53.98 cm, only 4 matches |
| Maximum measured discrepancy | Unavailable | 57.14 cm | 57.14 cm |
| Detected and within 10 cm of reference | 0/44 | 0/4 | 0/48 |

All four oblique errors are 53.22–57.14 cm. No automatic matched position is within 50 cm of its reference. Overhead localization error is **unavailable**, not zero: there were no valid detected/reference pairs.

The same four oblique stones manually marked at their visible body centres had 32.86 cm RMSE against the diagrams in the earlier experiment. The automatic model targets the coloured cap, which is higher above the ice and yields still worse ice-plane projections. Neither body-centre clicking nor cap detection is a validated footprint measurement.

For the 44 overhead targets, the earlier manual-centre projection had 3.99 cm median / 7.15 cm RMSE discrepancy. That is a manual reference audit, **not the automatic detector's score**. The detector fails before localization on these cases. Its oblique-view shape/colour rules reject round tops and can merge red stones into the red house paint.

## What was measured

- Existing frozen detector `colour-cap-baseline-v2` from `prototype/vision_core.py`, without retuning.
- Existing manually calibrated source frames from CBC's 2018 Olympic Canada–Switzerland mixed-doubles final.
- Published Olympic shot-diagram coordinates via the pinned CurlR extraction.
- Selected visible house stones within 2 m of the tee, not a complete board or all guards.
- Position discrepancy only after fixed same-colour image-space identity matching. Large metric errors are retained.

**This is a different recording from the Canada–Korea demo.** It tests the detector conditional on supplied manual calibration. It does not measure the automatic registration/rectification pipeline's whole-video accuracy, or establish physical stone accuracy on the customer-style video. No corresponding independent position reference is available for that clip.

## Freeze and provenance

`protocol.json` was saved before automatic predictions were generated. It fixes the source labels, camera transforms, old manual-to-diagram identity links, metric domain, matching gates, primary-frame selection, and success thresholds. It includes SHA-256 hashes of the detector, evaluator helpers, manual annotations, calibrations, reference links and coordinate records. The evaluation refuses to run if any frozen input changes.

There are 11 diagnostic frames, of which 9 enter the primary summary. `t398` repeats the board at `t414` and is excluded from the headline to avoid counting that duplicate view. `t469` is unsettled and has no valid post-shot position comparison. The deliberately partial frames at 231 and 309 s score only the annotated stationary red stones. Known moving stones are explicit exclusions. Unobserved stones are not counted as misses.

No detector parameter or calibration was changed in response to these measurements. The evaluator's first run required a NumPy-integer JSON serialization fix; prediction and matching rules were unchanged.

## Matching and error definitions

1. Convert the pre-existing 960×540 annotation-space homography to 1920×1080 source coordinates explicitly: `H_source = H_annotation @ diag(0.5, 0.5, 1)`.
2. Run the unchanged detector over the source frame, with its usual nominal-scale and grey-body checks. There is no clean registered background frame for this new source, so its optional reference-colour subtraction is disabled. This limits direct comparability to the source-specific Canada–Korea configuration.
3. Associate detections to existing manual visible-body labels using same-colour one-to-one assignment, prioritizing the maximum number of valid matches and then minimum normalized distance. The gate is fixed at 0.75 projected nominal stone diameters around the manual image label.
4. A matched in-scope target remains in the results even if its predicted coordinate falls outside the house. No automatic-position distance gate can hide a large localization error.
5. Convert the prediction to the pre-existing diagram orientation. Compute Euclidean discrepancy against that label's frozen diagram coordinate: `100 * norm(predicted_m - reference_m)` in centimetres.
6. Report misses and false proposals separately. Unmatched house-region proposals are false proposals against this visible annotation set. Known moving exclusions, unlabelled colours in partial frames and out-of-domain proposals are retained in the raw outputs with explicit statuses.
7. Joint success at 5/10/20/50 cm uses **all reference-linked targets** as the denominator, including misses. This prevents a small subset of successful detections from suggesting good overall performance.

Original manual-to-diagram links were established by the earlier audit with a 50 cm gate on **manual** projections. This means reference linkage is selected; it is not an unconstrained independent identity annotation. Links were fixed before this automatic benchmark. They are not recomputed from the new predictions.

## Reference limitations

- Diagram coordinates are not a physical survey. Scale is approximately 1.524 cm per extracted diagram pixel; actual diagram placement error is unknown.
- One oblique frame and four detected stones cannot establish typical oblique-camera accuracy or a useful population confidence interval.
- Eight overhead frames contain repeated stones across shots; the 44 observations are correlated, not 44 independent experiments.
- The same AI selected the manual landmarks and image labels in prior development. These frames were previously inspected; this is not a blind held-out evaluation.
- Per-frame manual calibration is supplied. Its uncertainty, reference quantization, shot timing and identity linking all contribute to measured discrepancies.
- Fully occluded stones and unlabelled moving objects are outside the scored visible subset.

The 1–2 cm figures from the separate rectification report measure **paint alignment** on another recording. They must not be cited as stone-position accuracy.

## Artifacts

- `results.json`: aggregate results, frame results, detections, rejected components and all per-stone errors.
- `stone-errors.csv`: downloadable per-stone statuses and measurements, including misses.
- `protocol.json`: frozen inputs, scope, thresholds, identity links and hashes.
- `frames/`: copied source images and the corresponding published diagrams for inspection.
- `run.log`: per-frame counts and metric summaries.
- `tests.txt`: unit test results, including non-censoring, one-to-one matching and missing-data handling.
- `browser-check.json`: report interaction and link checks.

## Reproduce

From the repository root:

```sh
feasibility/scripts/python.sh prototype/scripts/evaluate_stone_accuracy.py
feasibility/scripts/python.sh -m unittest discover -s prototype/tests
```

Do not overwrite `protocol.json` when improving the detector. Preserve this baseline and create a versioned evaluation run. The freeze script intentionally refuses to overwrite an existing protocol.

## Source records

- [CBC Olympic final footage](https://www.youtube.com/watch?v=qqXEvKF-lM8).
- [Official Olympic Results Book](https://curlit.com/PDF/OWG2018_ResultsBook.pdf), original pages 1202–1207, with extracted diagrams retained locally.
- [CurlR pinned at 2f997be34594ab79a133823177661aadfd9a318d](https://github.com/ritchi12/CurlR/tree/2f997be34594ab79a133823177661aadfd9a318d), records filtered to `OWG2018`, game 1. Extracted diagram pixels are converted to metres using the nominal outer ring radius. Dataset licensing does not extend to the video or original publication.
