# Original-resolution detection and calibration experiment

Open [the interactive viewer](index.html), or visit <http://127.0.0.1:8765/vision/index.html> while the local workbench server runs. It is linked from the upload page and from the full-video timeline. Exact-time matches in the timeline link to their experimental evidence.

## What was added

- Fourteen 1920 × 1080 frames from the existing Canada–Korea recording, split into 28 panel observations.
- Two manually specified reference calibrations, one per view. Four outer-ring/line intersections fit each ice-plane homography; nine inner-ring/tee landmarks per view are withheld from the fit.
- Feature-based registration to propagate each calibration only when sufficient, spatially distributed matches support a plausible transformation.
- A red/yellow visible-cap detector with scale, component-shape and grey-body filters, plus suppression of coloured paint already present in a clear reference image.
- Original-image overlays, experimental ice-plane cap projections, error examples, reference-label toggles and JSON evidence.
- A small, explicitly scoped labelled set and reproducible evaluation.

This is source-specific analysis. It has **not** been applied to arbitrary uploads or every sample in the full-video index.

## Results

| Set | Panel frames | Reference caps | Matched | False proposals | Missed |
| --- | ---: | ---: | ---: | ---: | ---: |
| Development | 7 | 13 | 13 | 1 | 0 |
| Same-match check | 7 | 9 | 7 | 2 | 2 |

Check precision and recall are both 7/9 (77.8%). Matched check-cap median error is 4.17 **source pixels**, RMSE 4.72 pixels. These describe cap detection against AI-selected image points; they do not measure metre accuracy, complete-board correctness or independent generalisation.

The check detector/reference hashes were recorded in `check-freeze.json` before computing check metrics. The check images were already visually inspected during annotation. This is not a blind test or a held-out event. Do not tune against these check failures and continue describing the set as untouched.

Visible failures include touching red caps merging into a rejected component, a yellow delivery-stick head counted as a cap, and a red object on player equipment counted as another cap. The development false proposal is also on player equipment.

## Calibration accuracy is not stone-position accuracy

Same-image withheld ice-landmark RMSE:

- Left: **1.24 cm** across nine landmarks.
- Right: **2.26 cm** across nine landmarks.

These are residuals against nominal painted geometry, using clicks made by the same AI implementing the method. They do not include external surveying, independent annotation, camera-registration error on other images, lens effects, or stone height.

Most importantly, a coloured stone cap sits **above the ice plane**. Applying an ice homography to its image coordinate creates parallax error, especially in the shallow right-hand view. Consequently:

- Outputs are called `ice_plane_projection_m`, explicitly **not** `stones_m` or measured stone centres.
- Camera coordinates remain view-local; left and right have not been aligned into a common throwing orientation.
- `two_pixel_sensitivity_m` is the mapping's response to a two-pixel offset, **not** a calibrated uncertainty interval.
- Board completeness, in-play status and stone identities remain unknown.
- Simulator export is explicitly blocked.

## Labels and scope

`annotations/detection-reference.json` records centres of visible, separable coloured caps, ignore rectangles and outside-ROI caps. The scope is the target house/guard region up to the hog line, with a nominal sheet-width band. Moving caps are included when inside that region; no stationarity label is inferred.

Three originally annotated deliveries were found to be well beyond this fixed target-end ROI after explicit projection checks. They were retained under `outside_roi_caps` and removed from the board-region denominator before the final evaluation. `development-baseline-v1.json` predates that scope correction and is **not directly comparable** to the final development metrics. This history is retained rather than concealed.

Parked/in-play distinctions are unresolved. The right-hand 7469-second frame explicitly ignores an ambiguous grouped-stone area. Fully hidden stones are not measurable with this visible-cap evaluation; recall is not recall of the full physical board.

## Reproduce

Run from the project root using the existing feasibility Python environment:

```sh
# Frames are already local; this command fetches only any missing selected frames.
feasibility/scripts/python.sh prototype/scripts/prepare_vision_frames.py

feasibility/scripts/python.sh prototype/scripts/run_vision.py
feasibility/scripts/python.sh prototype/scripts/evaluate_vision.py --include-check
feasibility/scripts/python.sh prototype/scripts/build_vision_viewer.py
feasibility/scripts/python.sh -m unittest discover -s prototype/tests -v
```

Missing frame downloads require fresh yt-dlp metadata because signed media URLs expire:

```sh
.venv/bin/python -m yt_dlp --skip-download --no-playlist --dump-single-json \
  'https://www.youtube.com/watch?v=aWXo6XeUFQw' \
  > prototype/vision/source-metadata.raw.json
```

The original source frames, calibration clicks, reference labels and current results are retained. No external publication occurred.

## Implementation map

- `../vision_core.py`: planar geometry, gated image registration, cap proposals and export rejection.
- `../scripts/run_vision.py`: process the explicit original-resolution frame set, save proposals and overlay images.
- `../scripts/evaluate_vision.py`: same-colour one-to-one nearest matching within 20 source pixels, plus explicit ignore regions.
- `../scripts/build_vision_viewer.py`: build the interactive evidence viewer and link exact-time observations into the existing timeline.
- `../vision-viewer.html`: source overlay, reference labels, projection diagram and failure reporting.

## Verification and next work

The combined 14-test suite passes, including planar round-trip, degenerate calibration rejection, blank-image abstention, resolution mismatch rejection, known synthetic camera translation, static-paint suppression and blocked game-state export. These software checks do not replace physical validation.

Next priorities are footprint-aware stone localisation/parallax correction, a detector that separates touching stones and equipment, active-end/settled-state inference, and independent human-checked evaluation on a new recording. Avoid turning cap projections into confident stone positions merely because their image-plane matches are close.
