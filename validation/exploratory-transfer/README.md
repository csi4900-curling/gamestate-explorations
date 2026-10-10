# Automated exploratory transfer — 7 October 2026

No user annotation was required. The reserved 2025 Wetzikon event is still excluded.
The former manual-labelling task is optional future work, not a prerequisite to
continued development.

## Recording and fixed test

[Canada–Slovakia, 2024 wheelchair championship](https://www.youtube.com/watch?v=DXM6bfHR4o8),
source catalogue row 226. This is a different recording from Canada–Korea, but from
the same competition and a similar composite-camera setup; it is not a broad
cross-domain generalization test. Local source is `canada-slovakia.mp4` (360p).

The elapsed-time interval 1650–2760 s was selected before viewing frames or detector
results, to match the duration/offset of the previous experiment. It is not asserted
to be one complete end. The unchanged frozen detector used its original left ROI,
gate, direction and thresholds. `run-01/manifest.json` was written before inference
and records media/code/config hashes. No reference labels were supplied.

## Result and retrospective AI review

- 11,100 sampled frames at 10 Hz; 6,266 colour/body proposals.
- 15 provisional passage events. **This is not 15 verified throws.**
- T01 at 1772.088 s and T14 at 2646.940 s visibly follow the head region of a moving
  wheelchair player. Crops at −1, 0 and +1 s with the detector box establish the
  spatial association (`suspect-events.jpg`). These are AI-reviewed false-event
  examples, not a blinded independent annotation set.
- The other 13 events are retained without claiming independently verified accuracy.
  Missed deliveries were not exhaustively enumerated, so recall is unknown.
- Fixed-time overview frames show that camera roles/play direction change within
  the interval. Always treating the left panel as departure is not a full-match
  solution. Inferring end boundaries from the detected event count would be circular.

This run exposes a real transfer failure despite the earlier 16/16 same-end result:
colour, a neutral band and plausible motion can also describe part of a moving
person. Improve person/stone discrimination and camera-role handling on development
footage. Do not tune thresholds on the reserved Wetzikon event.

## Follow-up screen

A separate in-sample brightness check withholds the two reviewed player-head
candidates while retaining 13 other candidates and all 15 raw events in the
artifact. This is a development correction, not independent precision/recall.
See [the throw-event measurement gate](../throw-event-benchmark/README.md).

## Evidence and reproduction

Open [index.html](index.html) for a local overview and timestamped event list.
`systematic-frames.jpg` is a fixed-time overview; `event-evidence-1/2/3.jpg` show every
emitted event with its recorded image track. `run-01/results.json` contains the full
observations, counts and limitations. `review.json` records AI interpretation separately
from inference; no event was silently removed from the saved output.

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 feasibility/scripts/python.sh \
  prototype/scripts/run_transfer_probe.py \
  --video validation/exploratory-transfer/canada-slovakia.mp4 \
  --source-id DXM6bfHR4o8 --output /tmp/new-transfer-run
```

The runner rejects reserved source IDs, the reserved video path and exact copies
of its media. Its output directory must be new. Source-independent inference and
media preparation use bounded decoder/OpenCV threads on this host.

Acquisition note: an initial WebM download failed mid-stream; a chunked 360p MP4
retry succeeded. An initial processing attempt exhausted thread/memory resources
before inference; the completed run uses one OpenCV/decoder thread and constrained
BLAS threads. No detector thresholds changed for those operational corrections.

## Published benchmark route

[The CurlObserver probe](../curlobserver-probe/README.md) uses publisher-supplied
labels instead of user annotations. A deterministic 25-image probe of the frozen
proposal stage matched 8/102 labelled stone boxes at IoU >= 0.5. That component
is not a general whole-frame detector. The newer calibrated body detector was
not evaluated by that probe. Publisher tracking labels are also present and are
a useful next component benchmark; physical coordinates and full game states
still require different references.

Next work: group public data by source before training/evaluation, establish a
stronger stone/person detector, and test camera-direction changes. Keep this
exploratory recording and the now-inspected 25 images in the development partition.
No further manual labelling is requested from the user.
