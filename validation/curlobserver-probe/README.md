# Published-label component probe — 7 October 2026

This is a reproducible smoke test with publisher-supplied labels. It does not
require the user to annotate anything. It is not a full-pipeline or official
held-out benchmark, and it is not a test of the newer calibrated body detector.

## Fixed experiment

Source: [CurlObserver dataset](https://github.com/CurlObserver/dataset), pinned to
`2cfe61efede3c446957ee94aefa8df1345fc4684`. The repository's detection folders were
verified to contain 5,000 images and 5,000 label files. Its tracking folders contain
112 videos and 112 corresponding label directories; a first-frame label was checked
and contains normalized boxes, colour and a track ID. Labels are actually present,
not merely promised by a paper.

Selected 25 image indices evenly across 0–4999 before downloading or running
inference. `manifest.json` records the selection, frozen detector hash and policy.
The original passage detector's colour-proposal function runs at its usual 640×360
size, with the ROI expanded to the whole image. All other thresholds are unchanged.
Publisher boxes are mapped to the same resized coordinates. Same-colour, one-to-one
matching uses IoU >= 0.5; unmatched boxes and proposals count as misses and extras.
This box metric does not measure ground-plane centre accuracy.

## Result

- 102 labelled stone boxes; 93 proposals.
- 8 matches, 94 misses, 85 extra proposals.
- Precision 8.60%; recall 7.84% on this particular sample.
- All eight matches occur in image 4582. The sample is small and correlated;
  do not interpret it as a population accuracy estimate.

The fixed cap/body heuristic does not transfer as a general whole-image stone
box detector. Appearance/scale assumptions, full-frame distractors and the
cap-proposal versus whole-stone box convention can all affect this score. This
run does not isolate their individual contributions and no thresholds were tuned
to improve the score. The calibrated replacement detector requires camera inputs
that these image labels alone do not supply, so it was not silently substituted.

## How to use the dataset next

Use these 25 images for development diagnostics now. Before training a learned
replacement, identify and split by source match/video, not adjacent random frames.
The publisher's partition script uses an unseeded image shuffle; its declared split
is not proof of match-level independence. Overlap with earlier Olympic development
footage has not been ruled out. Freeze a separate evaluation partition before tuning.

Tracking labels can support a later identity/occlusion benchmark without user
labelling. They do not by themselves provide validated physical coordinates,
complete end context, intentions or cross-camera identity ground truth.

The README permits research use and requests citation; no broader commercial
licence conclusion is made. Sample files retain their publisher's terms.

```sh
feasibility/scripts/python.sh prototype/scripts/probe_curlobserver.py \
  --output /tmp/new-curlobserver-probe
```

`results.json` retains all reference/proposed boxes, counts and image/label hashes.
Downloaded images and labels are the exact pinned inputs. No Wetzikon media was
used. The lower-level box scorer has synthetic regression tests.
