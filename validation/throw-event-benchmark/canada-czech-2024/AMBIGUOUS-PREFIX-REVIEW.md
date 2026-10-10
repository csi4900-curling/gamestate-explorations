# Ambiguous path prefixes: full-match source review

The [nine-sheet source review](gap-review/ambiguous-prefix-review/manifest.json)
inspects every `ambiguous_far_entry_motion_paths` row in the original
116-candidate full-match motion artifact. Each sheet shows the moving shared
prefix and the first frame where alternative paths appear. The generator
checks the source-video and motion-artifact hashes; the circles are detector
proposals over decoded source frames. These are agent-selected development
cases, **not independent or exhaustive labels**.

| Candidate | Source review | Integrated 91-candidate screen | Finding |
| --- | --- | --- | --- |
| [S33](gap-review/ambiguous-prefix-review/s33-prefix.jpg) | Red stone moves toward the near house, then another red proposal appears near a player. | Abstained | A real stone-like approach is lost because the path is not unique. Do not append the later player-adjacent branch. |
| [S39](gap-review/ambiguous-prefix-review/s39-prefix.jpg) | Red stone moves into a cluster of existing stones. | Accepted through existing shared-prefix support | Positive control; no new event. |
| [S40](gap-review/ambiguous-prefix-review/s40-prefix.jpg) | Yellow stone approaches another yellow stone; two yellow bodies move after the split. | Abstained | The [denser contact review](gap-review/s40-branch-source-review.jpg) supports a possible collision. Post-contact identity is unresolved. |
| [S54](gap-review/ambiguous-prefix-review/s54-prefix.jpg) | Red stone crosses the right camera and reaches the house. | Withheld as a shared timed-path duplicate | Positive duplicate control; do not count twice. |
| [S80](gap-review/ambiguous-prefix-review/s80-prefix.jpg) | Red stone moves toward an existing red stone. | Abstained | Visible short incoming motion is lost at the split. |
| [S84](gap-review/ambiguous-prefix-review/s84-prefix.jpg) | Red stone moves toward the house; the prefix has only two half-second samples. | Abstained | Visible incoming motion, but too short for the current unique-path rule. |
| [S90](gap-review/ambiguous-prefix-review/s90-prefix.jpg) | Red stone approaches an existing red stone. | Abstained | Visible incoming motion is lost at the split. |
| [S131](gap-review/ambiguous-prefix-review/s131-prefix.jpg), [S132](gap-review/ambiguous-prefix-review/s132-prefix.jpg) | Same red stone and identical two-point shared prefix and alternative paths. | Both abstained | One motion observation from two early-ROI triggers; any rescue must deduplicate them. |

Thus six **distinct withheld candidate windows** (S33, S40, S80, S84,
S90, and S131/S132) contain a visible moving stone at the proposed prefix.
That is stronger source evidence than the screen's `no supported motion path`
status suggests. It does **not** prove six missed physical throws: passage-to-
stone identity, release, exact contact outcome, event boundaries, and
exhaustiveness remain unverified. The S39 accepted case and S54 duplicate show
why a prefix rescue needs the existing duplicate screen and cannot simply add
every ambiguous row.

The [pre-split proposal audit](PRE-SPLIT-PROPOSAL-RESULTS.md) applies the same
frozen stone-patch model to all nine prefixes and groups S131/S132, yielding
six partial review proposals without changing the event screen.

A useful detector revision is to keep the pre-split motion as a partial event
observation, score appearance on that prefix, and open separate hypotheses for
the bodies after contact. It must abstain on post-contact identity until
continuous frames or other evidence resolve it. Evaluate that rule across
other recordings before replacing the frozen screen, and use independent
exhaustive labels to measure precision and recall. The frozen 79-candidate
screen and 91-candidate development screen are unchanged by this review.
