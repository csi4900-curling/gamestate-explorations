# 2024 split-panel camera-registration audit

This development audit asks whether the 2022 ice-region camera-motion
measurement can be **geometrically adapted** to the 2024 full-resolution
split-screen broadcast. It does not measure throw-event precision, recall or
F1. The [initial machine-readable result](split-panel-registration-reviewed-paths-development.json)
contains every positive path pair and source lineage. The later
[edge-guard rerun](split-panel-registration-reviewed-paths-edge-guard-v2-development.json)
is the current development rule. Run it with
`feasibility/scripts/python.sh prototype/scripts/audit_czech_split_panel_registration.py`
after preserving the existing output.

The input is the existing set of 21 source-reviewed moving-stone episodes in
`full-reviewed-stone-replay-gaps-development.json`. Seventeen have a provisional
path with at least two 1080p pixel centers; four have no such path. These paths
were selected through development review and cross-resolution candidate
alignment, so they are **positive examples only**, not a complete physical
throw reference. The replay ledger names the 360p source hash because that
source anchored its episode timeline. The runner checks that the later
full-resolution handoff includes the exact replay-ledger hash and that the
recorded seven-checkpoint 360p↔1080p alignment has zero time adjustment. It
also hashes the actual 1920×1080 video used for frame decoding.

Each path is assigned by its pixel x coordinate to the left or right
960×1080 panel. Its panel is resized without changing aspect ratio to
640×720, and its path pixels undergo the same 2/3 scale. A path crossing the
panel boundary would be rejected. The ice-like-region Lucas–Kanade/RANSAC
rule retains the 2022 saturation, brightness, feature, inlier and reliability
parameters; the top overlay mask scales from 70/360 to 140/720. Each adjacent
0.5 s path pair is registered as two 0.25 s source-frame transforms. Both
short transforms must pass. This is an **adaptation** of the Norway-developed
rule, not an unchanged full-frame transfer: the 2024 layout and panel aspect
ratio differ. It does not rectify either panel to rink coordinates.

| Observed quantity | Result |
| --- | ---: |
| Reviewed episodes with usable paths | 17 of 21 |
| Paths in left / right panel | 10 / 7 |
| Adjacent path pairs registered, initial rule | 160 of 160 |
| Short frame-pair registrations, initial rule | 320 of 320 |
| Median camera-relative path displacement | 22.669 px per 0.5 s pair |
| Median absolute change from raw displacement after registration | 0.174 px |

All 160 initially registered pairs have residual displacement above 5 px at
the 640×720 analysis scale. The edge-guard rerun registers 151/160; all 151
registered pairs remain above 5 px, and nine pairs abstain because a proposed
camera transform conflicts with scene-edge evidence. These outcomes are
consistent with the reviewed moving paths, but they do **not** validate 5 px
as a threshold for this layout. The
raw-versus-corrected difference is small for most pairs, so these examples
also do not demonstrate strong correction of camera motion. The
[quiet-board control audit](SPLIT-PANEL-REGISTRATION-CONTROLS.md) exposed
foreground-driven registration failures and shows why a displacement threshold
alone remains unsafe. Further testing needs verified stationary stone and
non-stone candidate controls, deliberately sampled camera changes, and
exhaustive independent physical throw labels. Only those can establish whether
the method suppresses false events while retaining true ones. The currently
measured source pixels do not establish persistent stone identities, metric
trajectories or simulation-ready game states.

The implementation is in
[`split_panel_camera_registration.py`](../../../prototype/split_panel_camera_registration.py)
and the runner is in
[`audit_czech_split_panel_registration.py`](../../../prototype/scripts/audit_czech_split_panel_registration.py).
The six focused registration tests include a synthetic camera translation
with an independently moving target; they pass under the project Python
environment.
