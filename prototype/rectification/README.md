# Metric ice-plane rectification

Open **http://127.0.0.1:8765/rectification/**. The workbench and continuous-detection page both link here.

This experiment transforms the actual camera pixels into an equal-scale, top-down **ice plane**. It does not synthesize a physically correct overhead view of elevated objects. Stones and people stretch because their visible surfaces are not on the calibrated plane.

## What runs

- Source: Canada–Korea 2024, YouTube `aWXo6XeUFQw`, source time 37:40–39:10. The existing local 90-second, 1920×1080, 30-fps clip is the input.
- Two separate camera panels. No cross-camera identity or coordinate fusion.
- A metric 4.20 × 4.20 m house crop, 140 pixels/metre on **both** axes, producing 588×588 videos.
- All 2,700 frames transformed per camera. No frame slideshow. The browser plays precomputed video, with a synchronized source crop and optional geometric guides.
- Every frame has a stored homography or an explicit unavailable result in `timeline.json`.
- This is source-specific. Generic uploads still run the original indexing path.

## Calibration and evidence separation

1. Initialize an image-to-ice homography from four manually selected outer-ring/line intersections on a clear reference image. These anchor orientation and handedness as well as scale. Left reference: source second 750; right: 6495. They are outside the rendered passage.
2. Use nominal radii **1.829, 1.219 and 0.610 m**. Search along the normal of each projected ellipse for colour/ice transitions with subpixel peak interpolation.
3. Fit on 180 outer/middle boundary observations per camera, using a robust nonlinear least-squares objective. Original four intersections remain weak pixel-space anchors. Normalize input pixels for numerical conditioning.
4. Exclude 60 interleaved outer/middle angular observations from the objective. Exclude the entire inner ring. Also report 2D errors at the four manually clicked inner-ring intersections and tee. Middle-ring manual clicks are no longer described as withheld because the middle boundary now participates in fitting.
5. Store all fit/check observations, original/refined matrices and before/after residuals in `calibration.json`.

| Check (RMSE, cm) | Left before → after | Right before → after |
|---|---:|---:|
| Unused outer/middle angular samples, radial | 1.37 → 0.97 | 2.44 → 1.68 |
| Entire unused inner boundary, radial | 1.14 → 0.91 | 2.22 → 2.03 |
| Clicked inner intersections + tee, 2D | 1.41 → 1.00 | 2.63 → 2.06 |

These are **same-image paint-alignment checks**, not surveyed physical positions, independent human ground truth, stone errors or confidence intervals. Neighbouring samples are correlated. Boundary search is initialized near the existing projection; occluders and colour transitions can produce spurious candidates. Nominal radii and manually clicked references introduce uncertainty not measured by the residuals. Radial error does not measure rotation; the separate point checks help assess orientation.

## Following the video

Absolute SIFT feature registration against the reference runs every 0.5 s (and sooner after failure or a large scene change). The refined reference homography is transported into the current image using the inverse registration transform.

Between absolute registrations, forward/backward Lucas–Kanade optical flow tracks a spread of reference-consistent ice features. RANSAC estimates the incremental plane transform. Re-anchoring limits accumulated drift. No stale transform is returned if an update fails.

Acceptance checks:

- Absolute registration: at least 12 inliers, broad spatial support, ≤2 px registration RMSE and ≤120 px maximum reference-corner movement. These existing limits deliberately reject large camera changes.
- Ring check on absolute frames: ≥50 boundary observations, ≥8 of 12 angular sectors, ≥2 rings with 12 observations each, median normal discrepancy <1.5 px, 90th-percentile normal discrepancy <3 px, 95th-percentile radial discrepancy <18 cm.
- Intermediate flow: forward/backward discrepancy <0.75 px; ≥16 RANSAC inliers with broad support; <0.7 px inlier RMSE; 90th-percentile per-frame movement <20 px.
- Mask feature seeding to the reference ice region and exclude large appearance differences, reducing tracking of players and stones. This is not semantic ice segmentation and cannot guarantee all surviving features lie on the ice.

These thresholds are engineering gates, **not calibrated confidence scores**. All parameters reside in `rectification_core.py`. Each frame records the age of its latest ring check; intermediate frames are not described as independently rechecking the rings.

Result: left **2,700/2,700** frames supported; right **2,688/2,700**, with 12 explicit unavailable frames. The total render/encode took about 262 s on this machine; not a standardized speed benchmark. `video-quality-summary.json` reports image-evidence residuals throughout the passage. Acceptance percentage is not an accuracy percentage.

## Additional checks

- 25/26 non-reference view/timestamp combinations from the existing same-match frame collection pass the gate; one is rejected. These images were previously inspected in development and are not a held-out match.
- Known synthetic camera translation and zoom/perspective transforms preserve the reference's metric coordinates at 81 test points per view. RMSE is below 0.06 cm in these synthetic cases. This tests propagation relative to the supplied calibration; it does **not** imply submillimetre real-world accuracy.
- 26 total project tests pass, including 9 added rectification tests: equal-axis scaling, train/check separation, blank image rejection, wrong-geometry rejection, camera-motion compensation, scene-cut abstention and camera-panel masking.
- Browser playback, camera switching, seeking, unavailable-frame display, guide toggling, reference comparisons and mobile layout are checked separately in `browser-check.json`.

## Architecture

```
clear reference + nominal rings + line intersections
    → robust metric reference homography
video frame → absolute registration OR checked optical flow
    → current image-to-ice homography + validity evidence
    → metric pixel warp → rectified video
                        → per-frame JSON → synchronized diagnostic viewer
```

For a source pixel p, the metric ice point is q ∝ H p. The output image uses a fixed metric-to-pixel matrix C, so the image warp is C H. Both axes have the same metres-to-pixels scale.

The implementation does not recover a unique 3D camera angle or height. Decomposing a plane homography into camera pose requires camera-intrinsic information or additional assumptions. Those are not established for these cropped/composited streams.

## What this does not solve

- **Elevated stone surfaces.** A cap-centre pixel is not a ground-centre measurement. Do not reuse the rendered cap positions as accurate stone coordinates. Footprint estimation or a justified 3D camera/stone model is still required.
- Lens distortion, independently surveyed ring dimensions, occluded markings, or physical position ground truth.
- Whole-sheet accuracy. This experiment validates around the house, not distant guards/hog-line extrapolation.
- Arbitrary camera layouts, automatic calibration initialization, large camera cuts, or robust recovery on a new recording.
- Persistent stone identities, shot segmentation, score inference, complete board states or simulator export.

## Reproduce

From the project root, using the existing Python environment:

```sh
feasibility/scripts/python.sh prototype/scripts/calibrate_rectification.py
feasibility/scripts/python.sh prototype/scripts/render_rectification.py
feasibility/scripts/python.sh prototype/scripts/audit_rectification.py
feasibility/scripts/python.sh -m unittest discover -s prototype/tests
```

Rendering needs local `ffmpeg`, the reference JPGs and `prototype/continuous/clip.mp4`. SciPy is added to `prototype/requirements.txt`. `core_sha256` in the render and audit artifacts identifies the implementation used.

## Sources

- [World Curling, Rules 2025, sheet dimensions](https://worldcurling.org/wp-content/uploads/2025/08/Rules-2025.pdf): nominal concentric-ring radii and ice-line geometry. These dimensions are assumptions for the recorded rink, not a survey of it.
- [OpenCV: homography and perspective correction](https://docs.opencv.org/4.13.0/d9/dab/tutorial_homography.html): planar mapping and the role of camera intrinsics in pose recovery.
- Extracted reference evidence: `geometry-sources.json`.
