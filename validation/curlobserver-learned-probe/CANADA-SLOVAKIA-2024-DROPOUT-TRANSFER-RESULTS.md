# Canada–Slovakia 2024: fixed fourth-recording dropout probe

The conditional cap-dropout screen was run **unchanged** on the Canada–Slovakia 2024 source interval 1650–2760 s, after its [pre-inference freeze](CANADA-SLOVAKIA-2024-DROPOUT-TRANSFER-PLAN.md). It retained **17 provisional events from 25 corridor passage candidates**. This is an operational transfer across a fourth same-production recording, **not** a precision/recall result: this interval has no exhaustive throw reference, and its older exploratory evidence was already exposed.

The [raw span detector](../throw-event-benchmark/canada-slovakia-2024/frozen-span-raw.json) emitted 27 candidates from the 360p full match. The fixed x=160±60 px [corridor](../throw-event-benchmark/canada-slovakia-2024/frozen-span-corridor.json) retained 25. The separate 1920×1080, 30 fps, 1110.033 s interval has SHA-256 `cd5799da6d851e01c365b5f4aeeb2fb10b068e6d726d273ac129ad8f87330077`. A [six-time alignment audit](canada-slovakia-2024-highres-alignment-transfer.json) selected zero source-time adjustment at every sampled checkpoint.

| Stage | Candidate outcome |
| --- | --- |
| [Raw receiving-motion scan](canada-slovakia-2024-candidate-centric-motion-transfer.json) | 17 unique paths; 1 ambiguous; 7 unsupported. 14 of 600 target samples rejected registration. |
| [Still-camera registration hold](canada-slovakia-2024-candidate-registration-hold-transfer.json) | 6 transforms conditionally borrowed; path counts unchanged. |
| [Bounded-gap selection](canada-slovakia-2024-candidate-motion-with-gaps-transfer.json) | Path counts unchanged. |
| [Conditional dropout rescue](canada-slovakia-2024-candidate-dropout-rescue-transfer.json) | 17 existing paths preserved; no new rescue accepted; 8 candidates abstained. |
| [Cap-patch and timed-path screen](canada-slovakia-2024-candidate-dropout-rescue-screen-transfer.json) | 17 provisional events retained; 8 withheld. No timed-path duplicate pair reached the frozen criterion. |

The 17 provisional events include **four positive-y** passages and **thirteen negative-y** passages. This matters because the older left-only detector did not handle the direction change throughout the interval. Their timestamps, colours, path evidence, and decisions are preserved in the screen artifact. Neither the count nor the alternating colours proves a complete end or a physically correct stone sequence.

The older [retrospective source review](../exploratory-transfer/review.json) flagged player-head detections at 1772.088 and 2646.940 s from a **different detector**. The fixed new corridor has no candidate at the first time: its nearest raw S03 at 1769.78 s (x≈74 px) lies outside the corridor. Near the second old flag, raw S26 at 2646.970 s (x≈43 px) is also outside the corridor. The corridor does retain a separate S25 at 2646.434 s (x≈217 px); the receiving-motion scan finds no supported path for S25, so the final screen withholds it. The timing and position of S26 are consistent with the old head region, but object identity between detector outputs has not been verified. These rejections are useful evidence, not an independently measured false-positive rate.

The strongest remaining gap is validation coverage. We do not know how many genuine throws occurred in this interval, whether any of the 17 accepts are false, or whether the eight withheld candidates include missed throws. Full-match scene changes, exact release/settle times, continuous stone identity, settled boards, and simulation inputs remain unverified. A frozen run on a recording with independent exhaustive event labels—and preferably a different broadcast camera family—is required before high-F1 claims.

A later [post-event observation pass](CANADA-SLOVAKIA-2024-POST-EVENT-BOARD-OBSERVATIONS.md) records stable **partial** near-house stones after 14 of the 17 provisional events. It does not turn them into complete game states or change this event-screen result.

A separate [postscore S02 prefix audit](CANADA-SLOVAKIA-2024-ORIGINAL-PREFIX-FALLBACK.md) finds a plausible red-stone motion passage among the abstentions. It preserves the original five-frame path prefix and marks the continuation and throw identity unknown. This is a development proposal; the frozen transfer screen above remains 17 provisional accepts.
