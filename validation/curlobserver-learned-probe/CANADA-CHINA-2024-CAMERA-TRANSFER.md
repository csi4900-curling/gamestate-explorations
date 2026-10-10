# Canada–China 2024: split-camera registration transfer

Development audit, 8 October 2026. This checks whether the camera registration used for the Canada–Korea 2024 trajectory prototype can be carried to another match from the same production. It is not a stone-trajectory or physical-coordinate validation.

## Source and sampling

The source-only [benchmark selection](../throw-event-benchmark/canada-china-2024/SELECTION.md) fixes the full-match interval at source time 1650–2760 s and contains 18 coarse delivery windows. The existing 640×360 `source.mp4` is the full match and is unchanged. Registration needs the 1920×1080 dimensions of the calibration reference, so this audit uses a separate 1080p format-137 video copy for that interval, `source-1080p-1650-2760.mp4` (SHA-256 `3ce37eff9e53026c64725a6b72f8e4b2eb42a8ae94245c2e75b62c2c59f5a919`). Its source offset is 1650 s, confirmed by matching frames against the full-match copy at source times 1700, 2000, and 2600 s. The clip contains roughly six extra seconds at its end due to section clipping; those frames were not sampled.

The [registration runner](../../prototype/scripts/audit_2024_camera_registration_transfer.py) sampled the start, midpoint, and end of each coarse window: 54 frames. It applied the existing Canada–Korea calibration and per-frame SIFT registration to both halves. The frozen reference windows are agent-labelled source review, not independent truth.

| Setting | Left accepted | Right accepted | Right rejected |
| --- | ---: | ---: | ---: |
| 640×360 full match, 120 px limit | 0/54 | 0/54 | 54/54, resolution mismatch |
| 1080p, default 120 px limit | 54/54 | 5/54 | 49/54 |
| 1080p, development 160 px limit | 54/54 | 53/54 | 1/54 |

The 160 px limit is an explicit development override; the [calibrator](../../prototype/vision_core.py) still defaults to 120 px. The additional 200 px audit accepted the same 53 right frames, so it offered no coverage benefit. Accepted right transforms in the 160 px audit moved reference corners by 116.9–148.2 px (median 127.9), with 15–42 inliers (median 29) and 0.49–1.18 px fit RMSE (median 0.83). The one rejection, C03 at 1790 s, had only seven inliers and insufficient spatial support.

The [contact sheet](canada-china-2024-right-registration-contact-development.jpg) shows four sampled target frames beside the warped reference and red/green image edges. The painted house, horizontal line, and lower logos visibly align across those samples. Players, stones, and scoreboard contents differ because they are not static rink landmarks. This visual check supports a camera-registration transfer in those frames; it does **not** measure the accuracy of projected stone centres, prove that every accepted frame is correctly aligned, or link a stone across views.

## Artifacts and next use

- [Default 1080p audit](canada-china-2024-camera-registration-1080p-development.json)
- [160 px development audit](canada-china-2024-camera-registration-1080p-motion160-development.json)
- [200 px sensitivity audit](canada-china-2024-camera-registration-1080p-motion200-development.json)
- [360p resolution control](canada-china-2024-camera-registration-360p-development.json)

This removes a camera-registration blocker for a Canada–China stone-proposal pilot, but it does not yet establish a throw trajectory or game state in this match. The next check is to detect stones in the accepted frames, inspect candidate continuity around deliveries and cutaways, and compare visible rink landmarks and paired-view stone positions independently before claiming metric replay. Frames without registration must abstain; a prior frame's homography cannot be reused silently. The reserved unseen end remains untouched.

## Sparse stone-proposal pilot

The [stone-proposal runner](../../prototype/scripts/audit_2024_stone_proposal_transfer.py) then applied the existing colour-cap/body-support detector to exactly those 54 frames, using only accepted per-frame registrations. The [proposal artifact](canada-china-2024-stone-proposals-sparse-development.json) records 75 left proposals in 43 frames and 139 right proposals in 51 frames; the one rejected right-camera registration produced an explicit abstention. This is proposal coverage, **not** detection precision or throw recall. The reference delivery colour appeared at least once in 10 of 18 left-view windows and all 18 right-view windows, but parked stones can satisfy that count.

The [annotated contact sheet](canada-china-2024-stone-proposal-contact-development.jpg) reveals false proposals on red clothing in the left view (for example 2335 and 2605 s). Those false proposals receive plausible-looking ground coordinates, so a valid camera registration and conditional localization status do not validate a stone. The right view also contains multiple same-colour stones, so colour and a single frame cannot identify the new delivery. Temporal motion, physical continuity across views, and a board-state comparison are needed before constructing event-specific stone tracks. The detector's reported ±assumption sensitivity is about 0.06–0.08 m on the left and 0.13–0.18 m on the right for these proposals; these values do not include false positives or total calibration error.

## Dense C04 motion and stability pilot

For C04, the audit sampled both cameras every 0.5 s from 1890.0 through 1929.5 s, extending the coarse reference window by 14.5 s to observe the apparent settled position. All 80 frames registered in both views. The right view yielded exactly one red proposal on each of 56 consecutive samples, from 1902.0 to 1929.5 s; the other 24 samples had no red proposal. A [conservative same-view selector](../../prototype/stone_proposal_path.py) retained this single continuous run without filling missing frames. It requires one matching-colour proposal per sample, forward travel, bounded step speed, and at least 2 m of endpoint displacement. The selected path has 15.47 m projected endpoint displacement. A [five-frame visual sequence](canada-china-2024-C04-motion-contact-development.jpg) shows the marked stone progressing toward the house at 1902, 1905, 1908, 1911, and 1915 s.

The [extended path artifact](canada-china-2024-C04-extended-motion-path-v2-development.json) records a first visible-stability sample at **1917.5 s**: the proposal remains within a 2 px image-space radius over the next 5 s. This is a defined observation criterion at 0.5 s sampling, not the exact physical stopping time. The first stone observation at 1902.0 s is also not a release timestamp. The one-proposal run and image sequence make the association plausible for this event, but they do not independently establish physical identity, validate metric accuracy, resolve any collision, or provide a settled board or simulator-ready state. Similar dense audits must be run on other events and camera changes before claiming transfer robustness.

Dense audit inputs: [registration](canada-china-2024-C04-extended-camera-registration-halfsecond-development.json), [stone proposals](canada-china-2024-C04-extended-stone-proposals-halfsecond-development.json). The original 1890–1915 s [window-only path](canada-china-2024-C04-motion-path-development.json) is retained as a separate artifact to make the effect of extending the observation period reviewable.

A subsequent [all-window motion audit](CANADA-CHINA-2024-MOTION-COVERAGE.md) applies the directional selector across the 18 coarse delivery windows and records which paths branch near parked stones.
