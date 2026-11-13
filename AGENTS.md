# Standing instructions: evidence, transfer, and completion

## Authorship and attribution

- Do not add AI co-author trailers, sign-offs, signatures, or self-credit to
  commits, PR descriptions, source files, or other project work. In particular,
  do not add `Co-Authored-By` attribution for an AI assistant or its provider.
- Factual disclosure of AI assistance and required evidence provenance are
  permitted; they do not authorize the assistant to claim authorship.

## Active scope — supervisor-approved focus, 22 October 2026

- The primary objective is ONE reliable end-to-end pipeline for left/right
  split-screen curling broadcasts, reconstructing accurate stone trajectories
  in rink coordinates from departure and receiving observations.
- Stone identity is a first-class requirement: reliably associate the same stone
  across observations, trajectory fragments and both camera views; handle occlusions
  and distinguish same-colour stones. Candidate/track IDs alone do not establish
  physical identity. Report ambiguous assignments and identity switches explicitly.
- Reuse maintained upstream detection/tracking implementations where suitable;
  do not rewrite available algorithms. Compare candidate components on shared
  inputs and held-out recordings. Any hybrid must demonstrate its contribution
  against its components, including runtime, rather than accumulate heuristics.
- Broad transfer learning and other broadcast formats are deferred. The user's
  other project objectives remain, but do not displace trajectory reliability
  within this format as the main priority.
- New videos in this format must not require manually selecting calibration
  landmarks, supplying new homographies, or tuning thresholds/association rules
  for each recording. Any necessary camera alignment or geometry estimation
  must be automatic inside the same versioned pipeline, with explicit failures.
- One pipeline does not imply one numerical homography fits every camera pose.
  Share the geometry model and processing rules; handle framing changes within
  the pipeline without hidden per-video interventions. Do not repeatedly fit
  geometry without investigating whether a stable-camera mapping can be reused.
- Required product outputs also include both-end board state, game/end/score
  context with observed-versus-inferred provenance, and time-based kinematics.
  Rotation/revolutions are secondary: never infer a measured spin count from
  translation alone or from an ODE solver without identifiable angular inputs.
  See docs/LEFT_RIGHT_REQUIREMENTS.md for the acceptance contract.
- Evaluate the complete public pipeline: event detection, continuous observable
  tracking, camera association, geometry, coverage, gaps and synchronized viewer.
  Isolated models, plausible plots and partial-point counts are insufficient.
- Development changes are authorized toward this scoped objective, but preserve
  baselines and label changed runs as development. The evidence, regression and
  completion requirements below still apply; do not manufacture validation.

These requirements record the user's explicit instruction after unsupported
generalization and completion claims damaged their trust. Apply them to every
task in this repository, including reports and supervisor preparation.

## Preserve the experiment

- Before evaluating generalizability, identify and freeze the entire working
  pipeline: learned weights, preprocessing, tracking, calibration, association,
  thresholds, postprocessing, and configuration. Record executable commands and
  input/code/model hashes.
- First reproduce the previously successful end-to-end example through the same
  entry point to be evaluated. Make it a regression check. Do not substitute a
  partial reimplementation or silently omit stages.
- Run the frozen pipeline on new matches before modifying it. Preserve the
  original outputs and failures. Failures are results, not permission to alter
  the experiment and keep its original label.
- Changes informed by an evaluation match make subsequent results development
  results on that match. Keep them separate from frozen transfer results. A new
  generalization claim needs a new independent evaluation after freezing again.
- Routine repairs are authorized where the task allows them; this rule does not
  create an approval requirement. Report their effect on experimental validity.

## Distinguish what produced the result

- Explicitly distinguish learned model predictions, programmed heuristics,
  manually supplied calibration or labels, and agent visual judgments.
- Never describe agent judgments as model capabilities or as independent ground
  truth. Record who reviewed the evidence and whether predictions were visible.
- Output availability, event precision, object-at-pixel checks, geometry error,
  trajectory identity, continuity, coverage, and complete-pipeline accuracy are
  different measurements. Do not substitute one for another.
- Never call a source-point check validated trajectory accuracy. A successful
  homography fit or plausible plot does not establish physical accuracy.

## Verify before claiming completion

- Define the requested outcome and its acceptance checks before implementation.
  For an integrated pipeline, test the actual public entry point and resulting
  user-visible output, including failures and candidates with missing tracks.
- Verify source timestamps, video seeking, coordinate orientation/handedness,
  equal plotting scales, calibration behavior, association, and retained gaps
  when relevant. Component tests alone do not establish end-to-end correctness.
- Investigate an unverified caveat when tools/data permit it. If verification is
  impossible, name the concrete missing evidence or access and limit the claim.
- Say "complete" only for the scope actually verified. State remaining required
  work plainly; do not reframe unfinished work as an optional improvement.
- Preserve unfavorable results and known defects in reports. Do not inflate
  progress to make a meeting update sound stronger.
- If a prior claim was wrong, identify the exact claim, evidence, affected
  outputs, and correction. Do not silently replace results or shift blame to
  the user or footage for an integration regression.

## Current evidence boundary

As of the user's correction in this conversation, reliable end-to-end trajectory
generalization has NOT been established. The 2022/2024 integrated runs include
development after inspecting those matches, and their source-point scores do
not certify geometric or full-trajectory accuracy. Do not revive earlier
completion/generalization claims without new supporting verification.

## Explicit calibration exception — user instruction, 9 November 2026

The user explicitly instructed: “If the position of the rink cannot be learned
by an independent model reliably, then make that calibration step explicit.”
This permits an exposed operator calibration workflow, superseding the earlier
no-manual-calibration requirement for this workflow. Save the source frames,
physical marking inputs, reviewer, check results, validity intervals and mapping
with each run. No hidden agent correction, recording-specific inference script,
per-video threshold tuning, or invented learned capability is permitted. Manual
calibration and agent reviews are not independent trajectory ground truth.
