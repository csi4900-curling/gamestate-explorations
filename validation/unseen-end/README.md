# Independent end review packet

**Start with the [beginner walkthrough](START-HERE.html), then the two-delivery practice page. No unseen model evaluation has been run.**

1. Open [annotate.html](annotate.html) in a browser and select `source.mp4` from
   this folder. It is the full downloaded 720p recording, approximately 2 h 50 min,
   not a model-selected excerpt. Video and drafts stay local to the browser.
2. Read [PROTOCOL.md](PROTOCOL.md). The 2025 Wetzikon event is reserved; source
   identity, aliases and media hash are in [reservation.json](reservation.json).
   Disclose prior use for model tuning. The first complete end is selected by the
   reviewer from source footage, before inference. Confirm actual sheet/team context.
3. Enter reviewer name, independence declaration and prior-exposure notes. Set end
   start/finish. Label broad nonoverlapping delivery intervals and each post-throw
   board. After reviewing the whole selected end, confirm that every delivery,
   including uncertain ones, is recorded. Export at each session end. Browser
   backups restore saved observations and pending work on the same page/browser;
   exported files let you resume elsewhere.
4. Capture a settled board frame, choose red/yellow, and click visible stone centres.
   Mark complete only if *all* in-play stones, including guards, are accounted for.
   Click **Save marked board** when finished. Starting the next throw also saves the pending board; capture shows the selected throw and timestamp beside the controls. Record one board per throw. Use an incomplete board with notes if unobservable.
   Edit JSON for identity, release/gate intervals, exclusions or corrections. An
   unknown identity stays null. Source-frame pixels are not physical rink positions.
5. Save the final reviewed draft here as `reference-draft.json`. Send the file/path
   back to the coding agent. Model configuration and source-specific calibration
   still need to be frozen before running inference on this new camera layout.

Do not open predictions while labelling. No predicted labels are included in this
packet. The existing advanced pipeline is source-specific; downloading this recording
does not make its calibration compatible with the Canada–Korea experiment.

## Integrity and scoring commands

After human review:

```sh
feasibility/scripts/python.sh scripts/evaluate_unseen_end.py seal \
  --reference validation/unseen-end/reference-draft.json \
  --video validation/unseen-end/source.mp4 \
  --output validation/unseen-end/reference-v1.sealed.json
```

The seal validates reference coverage, records the media hash and writes a digest.
It is an integrity record, not independent verification of annotation quality.
Preserve both files before inference. Never overwrite scored labels.

Model output contract:

```json
{
  "source_sha256": "same video SHA-256 as sealed reference",
  "source_interval_s": [100, 1200],
  "model_freeze": {"code_hashes": {}, "config_sha256": "...", "frozen_before_inference": true},
  "manual_effort": {"setup_minutes": 0, "correction_minutes": 0, "corrections": 0},
  "events": [{"id": "P01", "colour": "yellow", "crossing_time_s": 150, "arrival_identity": null}],
  "boards": [{"id": "B01", "throw_id": "E01", "time_s": 180, "complete": false,
    "coordinate_frame": "source_pixels", "units": "px", "stones": []}],
  "identity_correspondence": {"method": "reviewed_source_link",
    "prediction_to_reference": {"local-track-7": "reference-stone-1"}}
}
```

Board requests share the human-selected IDs/timestamps and coordinate convention;
stone labels are withheld from inference. Missing boards/events may be omitted and
are counted as failures. Do not fill incomplete automatic outputs with human labels.
For known identities, establish a source-reviewed one-to-one correspondence to
reference identities and record it in `identity_correspondence`. Omit the field
if no correspondence has been reviewed; matching strings alone do not establish
identity correctness, and unmapped predictions count as identity abstentions.
Record the review effort under `manual_effort`. Arbitrary camera-local track
numbers are not comparable across systems.

```sh
feasibility/scripts/python.sh scripts/evaluate_unseen_end.py score \
  --seal validation/unseen-end/reference-v1.sealed.json \
  --predictions /path/to/frozen-model-predictions.json \
  --output validation/unseen-end/score-v1.json
```

Scoring checks reference integrity, source/time/coordinate agreement, duplicate IDs,
missing/extra throws, colour, identity coverage, missed/extra stones and full-board
correctness. Event precision, recall and F1 require the reviewer's full-end
declaration; colour-aware metrics are reported separately. Position errors are
reported per board with units and reference method. Incomplete boards remain
unscorable for full-state correctness, but their annotated stones contribute
to a separate visible-stone recall measure. That measure cannot establish
precision or completeness where the reference view is occluded.
Human-independent pixel labels still do not validate physical metric accuracy.
Model-freeze timing and reviewer independence require review; JSON declarations
alone cannot prove either. Acceptable product error/manual effort remain undecided.
