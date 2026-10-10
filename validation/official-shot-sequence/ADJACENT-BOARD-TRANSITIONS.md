# First adjacent video-derived board transitions

We scanned five adjacent counter-anchored deliveries, Sweden–Switzerland 2022 end two shots 10–14, around the previously successful shot-12 board. The [first source-only scan](swiss-end2-adjacent-video-boards-first.json) used the existing overhead and stone detectors, frames every two seconds from +4 to +30 after each counter update, and stopped 12 seconds before the next update. It used a source-only recording orientation fixed by the earlier audit. Official board positions were not loaded until the source-only boards and transitions had been saved.

Shots 10 and 11 yielded no accepted overhead frames. Shots 12, 13, and 14 each yielded **two stable video stones**. The separate [postscore comparison](swiss-end2-adjacent-board-comparison-development.json) found that all two stones in each of those three boards match the corresponding official diagram, with no official symbols left unmatched. This is a selected development case, not a complete-end board success rate.

The [source-only local transition record](swiss-end2-partial-board-transitions-first.json) compares anonymous same-colour positions within 0.10 detected house radii:

- **Shot 12 → 13:** one yellow observation remains within 0.0121 house radii; the red is no longer observed and a second yellow becomes visible. The candidate event linked to shot 13 by the delayed counter is yellow.
- **Shot 13 → 14:** both yellow observations remain, with apparent shifts of 0.0123 and 0.0238 house radii; no stone enters or leaves the *visible* board. The linked candidate event is red.

These are observations of partial boards. Even where the official diagrams retrospectively show complete agreement, the source-only export cannot know that all stones are visible, whether an observed yellow is the delivered stone, or whether an apparent disappearance reflects a takeout, occlusion, or view change. The broad event windows and delayed counters do not establish release, collision, or settle time. No physical stone ID, metric ice calibration, continuous path, or 3D state is inferred.

The [extended board export](pwg2022-video-partial-board-observations-v2.json) preserves the original seven snapshots and adds shots 13 and 14: **nine** partial boards, **26** video stone observations. The [extended event-to-board handoff](pwg2022-provisional-event-board-evidence-v2.json) source-links all nine boards to one provisional counter-backed event candidate and includes the two local adjacent transitions. Every record remains `simulation_ready: false`. The reserved independent source was not used.

A subsequent [first cross-recording transfer](CHINA-ADJACENT-BOARD-FIRST-TRANSFER.md) using the same scan rule on Canada–China end two produced only two partial one-stone boards from five shots, with no complete boards. The favorable Swiss sequence should not be treated as a general coverage rate.
