# Manual curling calibration feasibility pilot

Open **[report.html](report.html)** for the results, annotated frames and limitations.

This is a completed, assistant-annotated exploratory experiment on one public CBC highlights upload of the Canada–Switzerland 2018 Olympic mixed-doubles final. It is not an automated detector, a blind benchmark, or a claim of surveyed ground-truth accuracy.

## Reproduce

From the project root, with Python 3.13, FFmpeg and network access for any missing sources:

```sh
python3.13 -m venv .venv
.venv/bin/pip install -r feasibility/requirements.txt
bash feasibility/scripts/python.sh feasibility/scripts/prepare_sources.py
bash feasibility/scripts/python.sh feasibility/scripts/build_annotations.py
bash feasibility/scripts/python.sh feasibility/scripts/test_geometry.py
bash feasibility/scripts/python.sh feasibility/scripts/evaluate.py
bash feasibility/scripts/python.sh feasibility/scripts/build_report.py
```

The shell wrapper locates native zlib/C++ libraries on this Nix host; on other hosts it simply runs the project virtual environment. A video host can change download availability; the original video and SHA-256 hash are retained locally. The CurlR revision is pinned in `sources/CurlR_commit.txt`.

## Files

- `annotations/manual.json`: actual manually selected landmark/stone coordinates, fitting versus withheld points, state association, exclusions and reasons.
- `scripts/build_annotations.py`: readable source of the annotations. Edit this, then regenerate the JSON, to revise an annotation.
- `sources/provenance.json`: URLs, source hashes, dataset revision and PDF page numbers.
- `sources/frame_manifest.json`: requested and decoded timestamps and source frame indices.
- `sources/official_shot_diagrams/`: original 300×600 diagram images extracted from PDF pages 1202–1207, in shot order.
- `results/calibration_metrics.csv`: per-frame model, independent landmark error and click sensitivity.
- `results/landmark_errors.csv`: every fit/check landmark and residual.
- `results/measured_stones.csv`: manual image positions and calibrated metre coordinates.
- `results/stone_comparisons.csv`: colour-constrained, one-to-one matches and unmatched observations; missing stones are not silently imputed.
- `results/homographies.json`: image-to-local-metre matrices; see per-frame model labels because two matrices are affine fallbacks.
- `results/repeat_zoom_consistency.csv`: paired measurements of the same seven stones at two zoom levels.
- `results/initial_homography_attempt/`: preserved failed unrestricted-homography run.
- `results/before_motion_audit/`: preserved comparisons before two moving yellow stones were excluded after checking adjacent frames.

All image coordinates refer to the saved **960×540 review image**, not the 1920×1080 source. Use the review image for the saved matrices, or prepend a 0.5 pixel-coordinate scale for source-resolution pixels. Rectified images are illustrations, not additional accuracy measurements.

## Reference coordinate audit

CurlR coordinates are diagram pixels. The normalized house has tee `(149.5, 159.5)` and outer ring radius approximately 120 pixels. The conversion used is `1.829 / 120 = 0.0152416667 metres/pixel`. Raw PDF diagrams alternate orientation: a house centred near `(149.5, 439.5)` is reversed relative to CurlR's normalized convention. Do not apply the normalized transform directly to an unnormalized PDF image.

The top/bottom storage strips contain unused/removed stones, so reference matching excludes centres with `y <= 40` or `y >= 580`. Matching uses visible manually annotated stones, per colour, one-to-one assignment, and a fixed 0.50 m rejection gate. Official stones outside the image or behind people are not treated as missed detections. The report gives discrepancies for matched visible stones, not full-board recall. A 2.0 m distance from tee defines the reported house region.

The official diagram positions are reference measurements, not surveyed physical truth. Calibration landmarks are withheld from fitting but annotated by the same assistant; there is no independent human annotation or surveyed rink geometry. The source is edited highlights, the views were selected for visible geometry, frames/stones are correlated, and the two-point validation of affine fallbacks is weak. Do not generalize these results to arbitrary broadcast footage.
