# Layout-aware camera-motion routing

`prototype/layout_camera_motion.py` now accepts a frame pair only when the
preflight names a supported layout run for the **same source hash** and both
times lie inside that run. Times are local to the video passed to the preflight.
Pairs crossing a layout-run or split-panel boundary abstain. A 640×360 image
is routed as a 2022 single view or a 2024 split view according to the verified
layout, never by resolution alone.

| Layout | Source frame | Analysis frame | Registration |
| --- | --- | --- | --- |
| Beijing 2022 | 640×360 single view | source pixels | Ice-region composed residual |
| 2024 split | 1920×1080, two 960×1080 panels | 640×720 panel | Split-panel edge-guard registration |
| 2024 split | 640×360, two 320×360 panels | 640×720 panel, upsampled 2× | Same split-panel edge-guard registration |

The [source replay](camera-motion-route-two-layouts-development.json) checks
one frozen path pair on each route: China 2022 gives 131.355 px, Czech 2024
1080p gives 35.543 px and its aligned 360p source gives 35.56 px. Source,
preflight, path and code hashes are recorded in the artifact. These are
selected path checks, not throw-event accuracy measurements.

The 360p adapter was developed on Czech and checked on its
[reviewed moving paths and board controls](../canada-czech-2024/lowres-split-registration-positive-and-board-controls-development.json):
153/160 moving path pairs registered and all 153 exceeded 5 analysis-frame
pixels. Among 30 low-raw board-control pairs, 28 registered and none exceeded
5 px. Among 30 high-raw board-control pairs, 26 registered and 10 exceeded
5 px. Thus a residual threshold alone still admits some busy-board false
motion. The low-resolution source adds no detail when upsampled.

On a second recording, the unchanged adapter's
[Latvia end-six transfer](../canada-latvia-2024/end6-lowres-split-registration-transfer-development.json)
registered 40/40 selected moving-stone-pixel pairs above 5 px and 45/45
preboundary quiet-path pairs below 5 px. The earlier
[1080p transfer](../canada-latvia-2024/SPLIT-PANEL-REGISTRATION-TRANSFER.md)
showed the same split on those selected pairs. These are source-reviewed
development samples, not independently labelled physical throws or an
exhaustive negative inventory. In particular, camera-relative displacement
does not itself identify a stone, release, or settled game state.

The router can be called by later segmentation and evidence-join stages; the
span detector now retains its observed track points on newly generated raw
proposals, and `prototype/scripts/measure_candidate_camera_motion.py` can
attach a source-hashed motion sidecar to every proposal in a run. A
[20-second Czech replay](camera-motion-route-czech24-360p-95-115/raw-with-track-points-development.json)
reproduces the existing full-match first proposal S01 at 96.892 s and retains
11 source-track points. All prior S01 event fields match the full-match raw
record except `track_id`, which is local to the shorter replay. Its
[motion sidecar](camera-motion-route-czech24-360p-95-115/candidate-camera-motion-development.json)
registers the 96.4–97.4 s path at 49.172 analysis-frame px. This confirms
the end-to-end evidence handoff for one candidate, not the correctness of the
candidate or a validated motion threshold. Existing frozen raw artifacts do
not contain these points and need a new source run to produce this sidecar.

New `run_throw_pipeline.py` split-screen runs now write
`candidate-camera-motion.json` beside `raw.json`, `events.json` and
`triage.json`; `--resume` checks its source, input and code hashes. The
[integrated Czech 95–115 s run](camera-motion-integrated-czech24-95-115/candidate-camera-motion.json)
contains one raw proposal, one confirmed candidate and one motion row, all
with ID S01. It resumes without changing artifacts. The existing confirmed
event decision still does not use the pairwise motion measurement. Next
validation must audit all proposed and
missed event windows against independent physical throw labels, including
camera changes, players, sweeping and board movement. Until then this route
is a measured cue with explicit abstentions, not a robust end-to-end detector.

A [second integrated Czech run](camera-motion-integrated-czech24-s96-negative/candidate-camera-motion.json)
over 4028–4052 s deliberately includes candidate S96, whose later associated
path was [source-reviewed as a wheelchair
footrest](../canada-czech-2024/source-review/s96-review.json). The shorter replay
calls that path S04, with the **same 4037.326 s passage time** as full-match
S96. It registers **48.089 px** of camera-relative motion. All five raw
proposals in that window were withheld by the existing context stage; only
two had registered camera motion. The high residual cannot establish stone
identity or serve as a standalone precision filter. The source review applies
to the later associated path; its continuity with the raw trigger is examined
below. This is a development failure-mode check, not an independent error-rate
estimate.

## Complete Czech source audit

The [full-source run](czech24-full-camera-motion-v1/preflight.json) covers
0–6683 s with one supported split-screen span at 90–6570 s. The opening
0–90 s and final 6570–6683 s are explicit unknown-layout gaps (203 s total).
Its [proposal-motion reconciliation](czech24-full-camera-motion-v1/candidate-motion-audit.json)
confirms that all **147 raw colour/time proposals** in the supported run match
the earlier full-match raw inventory in order. The context stage confirms 96
and withholds 51. Camera registration succeeds for 128 proposals and abstains
on 19. Every registered residual is above 5 analysis-frame pixels (minimum
44.758, median 50.849). This threshold therefore separates **none** of the
registered raw proposals on this match. Raw candidates S96 and S143 have
48.089 and 49.925 px respectively; their **downstream associated paths** were
source-reviewed as wheelchair movement, but same-object continuity from each
raw trigger is unverified. The context stage withholds S96 in this routed
replay but confirms S143.

This is a full-source candidate audit, not full-match throw recall: unknown
layout spans and missed physical throws have no denominator here. It shows
that camera registration can quantify proposal motion reproducibly across a
long run, but apparent motion of a wheelchair footrest is still real
camera-relative motion. Stone identity and independent event labels are the
next requirements for a high-precision, high-recall detector.

The existing [1080p overhead-darkness pilot](../canada-czech-2024/OVERHEAD-DARKNESS-TRANSFER.md)
uses samples later than the early-ROI proposal in some cases. Newly generated
raw proposals now preserve both the at-confirmation path and subsequent
observed points inside the detector ROI. A
[source-frame replay of S96 and S143](czech24-full-camera-motion-v1/continued-overhead-pilot.json)
shows the handoff gap: S143 has 33 measurable continued boxes with dark
fractions up to 0.964, while six of S96's 11 boxes cannot support the
15–100 px-above measurement and the other five peak at only 0.033. The
earlier later-patch audit measured at least 0.911 for the path associated
with S96. The old feature therefore cannot simply be placed at proposal time
or attached to the short ROI track. The
[raw-to-downstream anchor audit](czech24-full-camera-motion-v1/raw-to-downstream-left-anchor-audit.json)
finds that raw S96's 4037.6 s centre and the downstream S96 path's 4037.5 s
centre are **183.032 px apart** in 1080p source coordinates. Only one of 60
left-view downstream rows has a near-time pair in the existing sampled data,
so this is a concrete S96 mismatch, not a measured global handoff rate. The
separate [raw S96 source-pixel packet](czech24-full-camera-motion-v1/s96-raw-source-review/REVIEW.md)
shows its tracked feature moving with a player/wheelchair edge rather than an
isolated stone; that is same-agent review of the **raw** track, distinct from
the earlier downstream footrest review. The
system needs a reliable wider-view continuation and identity association
before later appearance evidence can filter the triggering proposal. Neither
low darkness nor an unmeasurable patch identifies a true stone.

A [conservative full-left-panel continuation
pilot](czech24-full-camera-motion-v1/wide-roi-continuation-pilot.json) uses the
same colour-cap detector in a wider 640×360 source ROI, predicts from recent
image motion, and requires a unique nearby next cap at each 0.1 s step. It
adds two points after S96's early-ROI track, then stops at a missing nearby
cap; it adds five after S143's track, then stops when two caps compete. It
neither bridges the S96 spatial mismatch nor claims a physical identity for
S143. The next tracking method must handle temporary segmentation loss and
multiple same-colour objects while preserving explicit uncertainty through
camera changes.

The [complete Czech raw-underpoint audit](czech24-full-camera-motion-v1/run-02/raw-underpoint-context-development.json)
measures the existing 1080p ice-context feature at three **raw pre-confirmation
cap points** for every one of the 147 proposals. All 147 have three readable
samples. Applying the prior descriptive boundaries (clear ≤0.05; cluttered
>0.25) to candidate medians gives 50 clear, 22 ambiguous and 75 cluttered.
Among the 96 context-confirmed candidates the counts are 48/17/31; among
51 withheld candidates they are 2/5/44. These are correlations with an
existing development gate, not physical stone labels. S96's median is 0.305
and S143's is 0.096, while IDs S07 and S69 are 0.388 and 0.348. Those IDs
have source-visible stone **downstream paths**, but continuity with their raw
triggers has not been verified. The overlapping values preclude a supported
raw-trigger stone decision from this feature; it is not promoted to a filter.

An [unchanged-feature Latvia transfer](latvia24-1650-2760-raw-context-v1/raw-underpoint-context-development.json)
uses the frozen 1650–2760 s 360p↔1080p alignment and the same three raw
pre-confirmation points. The new split-screen pipeline produces 27 raw
proposals, confirms 16 candidates and withholds 11; all 27 have measurable
underpoint context. The prior descriptive boundaries classify only 2 as
clear, 5 as ambiguous and 20 as cluttered. Of the 16 context-confirmed
candidates, **11 are cluttered** (median non-ice 0.399), compared with 31 of
96 context-confirmed Czech candidates (median 0.050). Thus even within the
same 2024 broadcast family, this raw-trigger geometry changes substantially
across recordings. These candidates have no independent stone/throw labels;
the result is a transfer diagnostic, not an estimated false-rejection rate.
The Latvia run resumes with its hashed preflight and proposal-motion sidecar.
The [cross-recording comparison](raw-underpoint-cross-recording-development.json)
pins both input and feature-code hashes and recomputes these tier counts.

The [end-conditioned direction audit](END-CONDITIONED-DIRECTION-AUDIT.md)
reconciles the Czech full-match candidate inventory with stable broadcast
end markers and checks a direction-switch cue on a Latvia interval. It
identifies source-visible player motion in two Czech opposite-direction
confirmed paths, while retaining the cue as review evidence rather than a
throw rejection rule.

The [cross-view corroboration transfer](DUAL-OBSERVER-TRANSFER.md) documents
two Czech stone passages lost by the surrounding-motion gate and the Latvia
source-review evidence showing why a missing right-camera proposal cannot
be used as a hard veto.

Reproduce the selected transfer and route replay with
`feasibility/scripts/python.sh prototype/scripts/transfer_latvia_lowres_split_registration.py`
and `feasibility/scripts/python.sh prototype/scripts/audit_layout_camera_motion_route.py`
after moving the existing JSON outputs aside. Both scripts verify source and
upstream artifact hashes before writing.
