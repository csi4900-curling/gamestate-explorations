# Latvia end-six camera-boundary check

The [reproducible audit](end6-field-of-view-censoring-development.json) checks why the 16 source-reviewed moving-stone-pixel paths stop shortly after the right-view motion onset. The native-1080p body template searched only to **y=970** in a **1080-pixel-high** frame. The final saved moving body centers lie at **y=803–945** (median 907), with **25–167 pixels** left before that search limit. A constant *image*-speed continuation of each final measured step would reach the frame bottom in **1.29–3.96 s** (median 1.90 s). That continuation is diagnostic only; it is not a recovered physical trajectory.

A one-second source-frame colour screen searches near each predicted cap center and abstains unless exactly one suitably sized component is within 30 pixels. It finds a **unique provisional same-colour component for 15 of 16** reviewed paths; **R01:A452 abstains**. Nine of those 15 component centers are already below the old y=970 search limit. This gives concrete short-tail candidates for later identity review, not 15 verified physical continuations. The rule and source subset were selected after source review and have no cross-recording score.

One selected source-frame check directly confirms a premature processing cutoff followed by actual view exit. For yellow path **R01:A401**, the prior body path ends at source time **5846 s**. In a fixed lower-right image region, the yellow component has **731 pixels at 5846**, **1,195 at 5847**, **404 touching the frame bottom at 5848**, and **none at 5849**. Source images show the same apparent stone moving downward, but this is same-agent visual continuity, not independently verified physical identity. The original y=970 search could not retain its 5847–5848 tail. The camera itself then loses the stone at the bottom of the frame.

This splits two failure modes that should be handled separately: enlarge the search region to recover source-visible tails where identity can be supported, and mark the eventual frame exit as **field-of-view censoring**. The last observation must not be labelled a physical settle. Extending this right-camera tracker alone cannot provide the rest of the throw or a simulation-ready trajectory; another view or later state observation must bridge the missing interval. The current left image around this selected event is a different, static end view and supplies no verified same-stone continuation.

The endpoint calculation covers all 16 reviewed stone-pixel paths, but the source-frame boundary witness is only for selected A401. Other paths can end early for additional reasons, including occlusion, template failure, or identity switching. There are no independent full-interval throw labels here, so this does not change event precision, recall, or F1.

The [censored event/state handoff](end6-censored-event-state-development.json) joins this boundary audit to all **20** end-six right-only review proposals and their later partial-image-board observations. It carries the 16 short high-resolution moving-body paths, 15 provisional next-second colour components, and 13 following partial boards as distinct evidence. The four person/clothing paths have no stone trajectory. Only A401 has the selected frame-edge witness; every row leaves physical settle, same-stone continuity to the later board, a complete metric board, and simulation readiness unresolved. The [exporter](../../../prototype/scripts/export_latvia_end6_censored_state.py) verifies both source-video fingerprints and all input lineages.

Reproduce from the frozen source and cross-resolution links:

```sh
feasibility/scripts/python.sh prototype/scripts/audit_latvia_end6_field_of_view.py \
  --body-links validation/throw-event-benchmark/canada-latvia-2024/end6-cross-resolution-body-cap-development.json \
  --video validation/throw-event-benchmark/canada-latvia-2024/source-1080p-5670-6670.mp4 \
  --output /tmp/latvia-end6-field-of-view-audit.json
```

The output fingerprints the video, linked-path artifact, and runner and refuses overwrite.

A separate [cap-seeded Italy/Estonia transfer](../RIGHT-COLOUR-TAIL-TRANSFER.md) finds next-frame colour components for all 25 source-reviewed moving-stone paths, but also for two of three person/wheelchair paths. This reinforces the distinction between pixel continuity and throw confirmation.
