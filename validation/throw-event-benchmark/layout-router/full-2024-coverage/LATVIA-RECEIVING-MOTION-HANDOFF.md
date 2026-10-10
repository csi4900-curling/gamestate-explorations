# Latvia full-match candidate sequence with right-camera motion evidence

The [receiving-motion handoff](latvia24-full-v1/full-match-candidate-receiving-image-handoff-development.json)
preserves all **127 ordered candidate rows** and every field of the existing
[full-match candidate/partial-state handoff](latvia24-full-v1/full-match-candidate-partial-state-handoff.json).
It adds `receiving_image_motion` only when a right-view image path was
source-reviewed as a moving stone and temporally associated with a provisional
left-camera candidate. The [joiner](../../../../prototype/scripts/attach_latvia_receiving_motion.py)
checks source and artifact hashes, colour agreement, review coverage, row
conservation, and false physical/simulation flags.

In the 1650–2760-s high-resolution excerpt, **11 candidates** receive this
extra image evidence: six red and five yellow. Each addition contains the
source-visible moving prefix as timestamped 1080p pixel centres. Three red
paths also have one-second *visual-stillness candidates*, while eight paths
remain right-censored before a visual stop. Long parked tracker tails are
excluded from the moving prefixes. These observations are image-space
evidence, not metric trajectories or proof that the left and right image
tracks are the same physical stone.

For the 5670–6670-s left-trigger blind interval, the handoff records the
complete [red](latvia24-full-v1/end6-highres-red-full-transfer-development.json)
and [yellow](latvia24-full-v1/end6-highres-body-handle-screen-development.json)
right-body probe result: no supported upward path under either frozen lane.
It explicitly leaves `interval_throw_free_verified: false`. No candidate is
added or deleted in that interval based on an absence of proposals.

All original `game_state_after` entries still lack physical end identity,
official shot identity, release/settle time, complete board, persistent stone
IDs, metric trajectory and spin count. Every `simulation_ready` flag remains
false. Independent full-video throw labels, reliable cross-camera stone IDs,
and complete post-throw boards are needed before this becomes a physical
game-state sequence or a coaching simulation input.
