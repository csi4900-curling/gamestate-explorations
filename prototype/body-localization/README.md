# Stone-body detection and conditional ground localization

Open **http://127.0.0.1:8765/body-localization/** for the benchmark comparison and the continuous-video demonstration.

The new implementation is `prototype/body_localization.py`. The failed `vision_core.py` detector, original benchmark protocol and original results are preserved unchanged.

## Result on the existing development benchmark

| Measure | Failed baseline | Body + camera v1 |
|---|---:|---:|
| Visible target observations | 48 | 48 |
| Detected and localized | 4 | **46** |
| Missed | 44 | **2** |
| False proposals in scored region | 4 | **0** |
| Detected and within 10 cm of reference | 0/48 | **40/48** |
| Median matched reference discrepancy | 53.98 cm (4 matches) | **4.22 cm (46 matches)** |
| Matched RMSE | 54.60 cm (4 matches) | **7.30 cm (46 matches)** |
| 95th-percentile matched discrepancy | 56.70 cm | **17.90 cm** |
| Worst matched discrepancy | 57.14 cm | **20.96 cm** |

The overall error populations differ because detection coverage changed. The cleanest height-correction comparison is the **same four oblique stones**: uncorrected RMSE 54.61 cm → corrected **7.53 cm**. The tiny discrepancy from the archived 54.60 cm baseline comes from the retained cap proposal's rounded/unrounded pixel projection, not a new identity match.

Overhead detections improve from 0/44 to **42/44**. Two primary targets remain missed (`t136 R2`, `t414 R3`). Six localized observations still exceed 10 cm discrepancy. These errors remain in the results.

**This is development performance, not a held-out accuracy claim.** These images and outcomes were already known; three overhead frames were used to inspect the new body proposal method. The benchmark uses manual per-frame calibration, existing identity links, and diagram-derived positions rather than surveyed physical coordinates. Repeated stones across shots are correlated. Do not cite 4.22 cm as accuracy on arbitrary videos or on the Canada–Korea clip.

## What changed

This is a **classical computer-vision and geometry baseline**, not a trained neural network.

### High-angle body detection

1. Use the calibrated image-to-ice homography to calculate expected local stone scale and foreshortening.
2. Generate circular stone-body outline proposals in the original image with OpenCV's gradient-based circle detector. Stone radius is assumed to be 0.139 m; the search scale derives from the calibration.
3. Check each proposal against local projected scale, a coloured interior and a neutral grey body rim. Colour verifies a body proposal rather than defining a connected blob, avoiding the old failure where a red stone merged into red house paint.
4. Suppress duplicate inner/outer outlines at the same centre.

The branch is selected when the local minor/major plane-Jacobian scale ratio at the tee is at least 0.65. Proposal support scores are ranking heuristics, not calibrated probabilities. Touching, heavily occluded, blurry or strongly non-circular stones remain difficult.

### Low-angle proposals

The old body-supported cap detector remains a proposal generator for low-angle images. Its colour, shape and grey-body checks are unchanged. Reference-paint subtraction is used when a registered clean source reference is available. The new model changes localization after detection; it does not claim to have solved all low-angle detection failures.

### Height-aware projection

Let `M = inverse(H)` map ground-plane coordinates into image pixels. Under assumed camera intrinsics, estimate a vertical image projection vector `v`. A feature at known height `h` projects using:

```
image_point ∝ (M + [0, 0, h*v]) @ [ground_x, ground_y, 1]
```

Invert this height-specific plane mapping to estimate ground `(x, y)`. This accounts for the cap being above the ice instead of applying the ice homography directly to it.

The camera model assumes:

- Zero skew.
- Principal point at the centre of the supplied camera panel.
- Square pixels by default.
- No lens distortion.
- A valid supplied ice-plane homography and the declared view-local coordinate convention.

The two plane-axis orthogonality/equal-scale constraints estimate squared focal length. Non-positive/unidentifiable focal solutions, inconsistent plane-axis constraints, or implausible camera height are rejected. A homography alone does **not** provide uniquely known camera intrinsics; this model is explicitly conditional on the assumptions.

Feature-height assumptions:

- Coloured-cap plane: **0.136 m**.
- Centre of a high-angle body outline: **0.068 m**.
- Stone body radius: **0.139 m**.

A primary Team GB source describes typical Olympic stones as 278 mm wide and 136 mm high. Using that height for the observed cap plane, and half the height for a body-outline centre, are **model assumptions**, not measurements of the cap/rim surface in these videos. They must eventually be independently calibrated. These constants were set before the new benchmark score was computed; diagram positions are never read by inference.

For near-overhead body outlines with local plane-axis ratio ≥0.75 and unidentifiable camera pose, the model emits the body-centre ice projection as an explicitly labelled approximation. It records a weak-perspective height-bias scale. Inconsistent low-angle cases emit no position.

## Continuous-video integration

`process_body_video.py` uses the existing source-specific, per-frame accepted ice matrices from `rectification/timeline.json`, then detects and localizes at 0.5-second intervals over the complete 90-second clip. Missing ice geometry yields no positions. The same lightweight, camera-local tracker provides provisional IDs.

For this fixed-camera recording, a conditional reference camera is transported by the accepted reference-to-current image homography. Re-estimating focal length from every noisy frame was unstable, so the reference is the camera prior. This assumes registration/zoom-like image changes; **physical camera translation and its elevated-object parallax are not modelled**. The generic one-frame API still estimates its own conditional camera when no prior is supplied.

The viewer shows the original video, uncorrected projections, conditional ground estimates, optional assumption-sensitivity circles, and per-stone metadata. It does not synthesize missing stones or certify a complete board. Generic uploads continue to use the older indexing workflow; automatic calibration on arbitrary recordings is not implemented.

The existing Canada–Korea cap-check annotations give **7 matches, 2 false proposals and 2 misses** on the check subset, unchanged from the original cap baseline. All nine emitted proposals in that subset have conditional positions, including the false proposals—height correction is not a semantic stone classifier. There is **no independent metric ground-position reference** for this recording. See `transfer-check.json`.

## Sensitivity, not confidence

For a conditional camera, the reported sensitivity is the largest position change under separate perturbations:

- Feature height ±2 cm.
- Pixel aspect ±10%.
- Principal point ±5% of camera-panel width/height.

These perturbations are one at a time, and variants without consistent camera solutions are skipped. The result is **not** a confidence interval, joint worst-case bound, probability or complete uncertainty estimate. It excludes detection error, imperfect calibration, reference error, and unmodelled distortions. A small sensitivity cannot validate a wrong feature/camera model.

## Evaluation discipline

- Original detector and original protocol hashes are checked on every benchmark run.
- Image-space matching and reference links remain unchanged. No metric-distance gate removes bad new positions.
- Body-model inference accepts only image, calibration, region and optional reference camera/background. It does not read benchmark annotations or reference coordinates.
- New benchmark results, continuous-video results and transfer checks each record the new model SHA-256.
- The primary benchmark still excludes one duplicate view and one unsettled frame. Partial frames still evaluate only the labelled stationary colour.
- The comparator records misses, position-unavailable detections and errors separately. No prediction is declared simulator-ready.

Forty total project tests pass, including eight new geometry/localization tests. Synthetic known-camera tests verify that height correction recovers ground coordinates and that reference-camera transport preserves them. Other tests cover ambiguous camera rejection, zero-height equivalence, missing calibration, blank frames and explicit sensitivity. Synthetic correctness is not a physical accuracy measurement.

## Reproduce

```sh
feasibility/scripts/python.sh prototype/scripts/evaluate_body_localization.py
feasibility/scripts/python.sh prototype/scripts/process_body_video.py
feasibility/scripts/python.sh prototype/scripts/check_body_transfer.py
feasibility/scripts/python.sh -m unittest discover -s prototype/tests
```

No new ML dependency or model-weight download is required. Existing OpenCV/NumPy/SciPy dependencies suffice.

## Artifacts

- `results.json`, `stone-errors.csv`: benchmark results and every target outcome.
- `video-timeline.json`: every sampled video estimate, image proposal, localization method and camera/sensitivity diagnostics.
- `transfer-check.json`: secondary cap detection results on the customer-style recording.
- `run.log`, `video-run.log`, `tests.txt`, `browser-check.json`: execution and verification records.
- `geometry-sources.json`: primary-source reference extracts.

## Sources

- [OpenCV: homography, perspective correction and camera pose](https://docs.opencv.org/4.13.0/d9/dab/tutorial_homography.html).
- [Team GB: typical Olympic stone dimensions](https://www.teamgb.com/article/ailsa-craig-everything-you-need-to-know-about-where-olympic-curling-stones/5EFRzBr6xItMWCr2XRyaTS).
- [Original benchmark and published-diagram provenance](../stone-accuracy/README.md).
