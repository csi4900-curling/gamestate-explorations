# Czech end 1: raw stone paths withheld by surrounding-motion gate

The split-screen pipeline's raw detector proposed red paths **S04 at
191.949 s** and **S13 at 488.651 s**. Its context stage withheld both as
`large_surrounding_motion`, with 1,257 and 1,253 changed pixels in the
80 × 80 context patch. The [lossless triage](run-02/triage.json) correctly
retains both as `needs_review`, but neither appears among the 96
context-confirmed candidates. This is a concrete recall failure if the
confirmed list is treated as the throw segmentation.

Unmarked, source-hashed frames show the raw tracked feature is a moving red
stone in both cases. For S04, the recorded center moves from (165.0, 93.2)
at [191.5 s](s04-raw-source-review/source-191.5.png) to (167.5, 68.08) at
[192.5 s](s04-raw-source-review/source-192.5.png). The stone continues up
the left view at [194 s](s04-raw-source-review/source-194.0.png) and
[196 s](s04-raw-source-review/source-196.0.png). For S13, the raw center
moves from (163.0, 88.0) at
[488.2 s](s13-raw-source-review/source-488.2.png) to (162.0, 64.0) at
[489.1 s](s13-raw-source-review/source-489.1.png), with the red stone
continuing at [490 s](s13-raw-source-review/source-490.0.png). The full
frames retain both cameras and the nearby players. The
[S04 manifest](s04-raw-source-review/manifest.json) and
[S13 manifest](s13-raw-source-review/manifest.json) pin the video, raw
proposal, context decision, code, frames, and raw boxes by SHA-256.

An [older cross-view handoff](large-motion-crossview-reconciliation-development.json)
provisionally supported both paths. It associates S04 with right proposal
`R01:A004` at 199.375 s (three of three stone-like patches); the red stone
is visible in the right panel at [198 s](s04-raw-source-review/source-198.0.png),
[200 s](s04-raw-source-review/source-200.0.png), and
[202 s](s04-raw-source-review/source-202.0.png). It associates S13 with
`R01:A014` at 495.14 s, whose sampled right pixels were previously reviewed
as a moving stone. These are corroborating observations, not verified
physical identity across cameras. The same older screen also provisionally
accepted S96, whose raw source pixels follow a player/wheelchair feature;
its acceptances cannot be used uncritically as ground truth.

A [development corroboration replay](dual-observer-corroboration-development.json)
requires a later right proposal within 20 s, at least two positive
stone-like patches, and at least two aligned high/low-resolution path samples
with median center distance ≤3 px at 360p. It flags 40 of 147 Czech raw
candidates. **S04 and S13 are the only context-withheld candidates among
those 40**; S96 does not satisfy the right-patch and overlap evidence. This
criterion was inspected on exposed Czech footage and is a hypothesis for a
stone-specific rescue stage, not a validated event classifier. The two
observers can also agree on the same wrong source pixels.

Both rejected candidates move in the dominant image direction for the
stable broadcast end-1 marker. S04 lies 47.154 s from the nearest
context-confirmed candidate; S13 lies 38.851 s away. The
[complete rejection inventory](large-surrounding-motion-rejections-development.json)
reports **18** candidates withheld for this reason across the full Czech
run, 17 within stable marker runs. A
[three-frame source review of all 18 raw tracks](large-motion-source-packet/REVIEW.md)
finds two moving stones (S04 and S13) and 16 player, staff, or wheelchair
features. This review classifies the tracked pixels, not every physical
event in the surrounding interval.

These are same-agent reviews of candidate-selected source frames, not
independent video-to-event labels. They establish stone passages at the raw
candidate locations, but not exact physical release times or complete
end-to-end stone identities across both cameras. A high-recall event system
must retain such proposals until stone-specific downstream evidence resolves
them. The current `events.json` alone is insufficient as the final event
list, and changing the broad motion threshold on these two examples would
have an unknown precision cost. Independent exhaustive throw labels are
still needed to measure that tradeoff.

Reproduce the packets with
`feasibility/scripts/python.sh prototype/scripts/export_czech_withheld_stone_source.py`
and the inventory with
`feasibility/scripts/python.sh prototype/scripts/audit_czech_large_motion_rejections.py`
after moving their frozen outputs aside. The cross-pipeline audit is
reproduced with
`python prototype/scripts/audit_czech_context_rejections_vs_crossview.py`;
the complete marked contact sheets with
`feasibility/scripts/python.sh prototype/scripts/render_czech_large_motion_source_packet.py`;
and the candidate corroboration flag with
`python prototype/scripts/audit_czech_dual_observer_corroboration.py`.
