# Unseen-end evaluation protocol v1 — 28 September 2026

Status: protocol prepared; independent annotations and unseen inference pending.
No independent accuracy result exists yet.

## Partition and selection (before predictions)

Reserve the entire 2025 Wetzikon event from the supplied catalogue for evaluation,
including aliases, panels and other recordings of the same event. Primary source:
catalogue row 302, CAN–SUI2, RR1, https://youtu.be/VzLqioK2DYk.
These are catalogue claims, not verified on-screen identities. This event is not
among the eight sampled development recordings in the recorded footage audit.
Prior viewing outside this repository is unknown: the reviewer must disclose it.
If prior model tuning used this event, reserve a different event before proceeding.

The independent reviewer chooses the first fully recorded end after opening
introductions, using only source footage. Record its start/end and sheet/panel
identity before running inference. Include the opening board, all deliveries,
settled post-throw boards and the final board. Do not choose an end because the
model performs well. If it is incomplete, log why and take the next complete end.
If media is unavailable, record that failure before selecting another source.
Before sealing, the reviewer explicitly confirms that the entire selected end
was checked and every delivery, including uncertain ones, was recorded. The
scorer requires this declaration before reporting precision, recall or F1;
it cannot verify completeness from JSON alone.

## Separation of roles

A user or teammate labels the source without predictions. The coding agent does
not create independent ground truth. Store drafts under `reference-draft.json`;
seal only after human review, then record a SHA-256 digest before scoring. A seal
records integrity, not proof of annotation independence. Corrections require a
new reference version and explanation, never overwriting a scored reference.

Manual source setup is allowed: panel bounds, direction, static rink landmarks
and nominal rink geometry. Record setup minutes and every change. Use a separate
setup interval outside the scored end. Freeze code, configuration, source hashes,
coordinate conventions and gate location before unseen inference. A gate studied
on Canada–Korea cannot be assumed to occupy the same pixels in this recording.
Do not tune detection thresholds, identity rules or gates against test errors.
If adaptation follows a failed test, report it as development and reserve a new test.

## What the human labels

Use seconds relative to the exact local video file (record any source-time offset).
For each actual delivery, record a unique throw ID, colour, a broad delivery
interval, and optional release interval. Record the crossing interval at the
frozen gate separately. A crossing is not a release. List arrival identity when
observable, and the interval in which all in-play stones are confirmed stopped.
Mark uncertain, off-camera and unobservable events explicitly; do not invent them.

For each post-throw board, record reference ID, throw ID, timestamp, whether the
whole in-play board is observable (including guards), and each stone's colour,
persistent identity if known, and image position. A missing stone is not necessarily
out of play. Preserve evidence timestamps and reasons for unknown completeness.
Metric reference coordinates require a documented independent measurement method.
Manual pixels projected by the detector's own homography can assess image agreement
but cannot establish independent physical position accuracy. Keep those metrics separate.
Record active label/review/correction minutes and correction counts.

## Frozen scoring policy

- Match predicted passage times one-to-one to broad human delivery intervals,
  with zero extra tolerance. Count every unmatched prediction and reference.
  Report event precision, recall and F1 from these matches. Assess colour
  separately after temporal matching and report colour-aware precision, recall
  and F1 as a second measure. This measures throw detection, not timing.
- Score gate timing only against annotations of that exact gate. Release timing
  is unavailable unless separately annotated and actually estimated by the model.
- Report known cross-view identity accuracy and coverage separately. A scored
  identity requires an explicit source-reviewed one-to-one mapping from the
  prediction's camera-local ID to the reference ID; matching ID strings alone
  do not verify identity. Unknown or unmapped predictions reduce coverage;
  never silently drop wrong identities.
- Score post-throw boards by reference ID at fixed human-selected evaluation times.
  Report supplied snapshot coverage and full-board correctness. A correct full
  board requires a complete prediction, exact stone count and colour, a bijection
  within the declared position tolerance, and no wrong known identities.
- Unknown-completeness references are unscorable for full-board correctness.
  Their annotated visible stones still contribute to a separate visible-stone
  recall and matched-position diagnostic. Do not infer false positives or a
  complete state from an incomplete reference. Missing predictions count as
  failures among scorable complete references and as misses for annotated
  visible stones.
- Position matching is by colour and distance, independently of track ID. Report
  misses/extras and identity errors as well as matched position error.
- Position tolerance: 0.10 m for independently supported metric references;
  5 source-image pixels for image-space agreement. Report the reference method,
  units, coordinate frame and denominator beside every result. These are diagnostic
  thresholds, not accepted product requirements. Shared projection is conditional.
- Report raw counts, error distribution, manual effort, runtime and all exclusions.
  One end is a pilot with correlated observations, not a generalization guarantee.

## Completion criteria

A frozen source/config/model record, independently sealed labels, all end events
and fixed-time board predictions (including explicit unavailable outputs), scored
report and error review. An unimplemented complete-board extractor must score as
missing predictions; it must not be replaced by manually corrected model outputs.
Publish automatic results first; optionally report human-assisted results separately.
No release-time or full-trajectory claim follows from a successful throw count.
