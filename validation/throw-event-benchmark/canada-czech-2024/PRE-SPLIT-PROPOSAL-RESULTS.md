# Pre-split motion review proposals

The [source review](AMBIGUOUS-PREFIX-REVIEW.md) found moving stones in six
distinct candidate windows withheld by the integrated 91-candidate screen.
The reproducible [proposal artifact](gap-review/pre-split-proposals-development.json)
now preserves these approaches **only up to the first ambiguous path frame**.
The rule requires at least two path observations, at least 1.0 m conditional
endpoint travel, and at least two positive frozen stone-patch samples on the
shared prefix. It excludes accepted candidates and already marked shared-path
duplicates; exact duplicate prefixes are grouped. It does not choose a
post-contact stone identity or change the event screen.

| Review proposal | Prefix observations | Conditional travel | Positive patch samples | First split |
| --- | ---: | ---: | ---: | ---: |
| S33 | 4 | 2.89 m | 3/3 | 1078.0 s |
| S40 | 4 | 2.49 m | 3/3 | 1520.5 s |
| S80 | 4 | 1.33 m | 3/3 | 3285.0 s |
| S84 | 2 | 1.05 m | 2/2 | 3581.5 s |
| S90 | 4 | 2.50 m | 3/3 | 3893.5 s |
| S131, with duplicate S132 | 2 | 1.02 m | 2/2 | 5725.0 s |

The [nine-row patch audit](gap-review/ambiguous-prefix-patch-audit.json) uses
the unchanged model and source registration on first/middle/last prefix
samples. All six groups pass. It also scores S39, already accepted, and S54,
already marked a shared timed-path duplicate; neither creates a new proposal.
The input [motion subset](gap-review/ambiguous-prefix-motion-subset.json)
is an exact extraction from the original full-match motion artifact, with its
parent hash preserved. `prototype/scripts/extract_ambiguous_motion_subset.py`
recreates that subset; `prototype/scripts/audit_candidate_path_patch_appearance.py`
recreates the patch audit; and
`prototype/scripts/audit_pre_split_motion_proposals.py` applies the fixed
review rule and records all input and code hashes.

The same rule, without retuning, produced [one previously known Latvia S21
proposal](../../curlobserver-learned-probe/pre-split-development-transfer/latvia-proposals.json)
and zero on the [Italy](../../curlobserver-learned-probe/pre-split-development-transfer/italy-proposals.json),
[Estonia](../../curlobserver-learned-probe/pre-split-development-transfer/estonia-proposals.json),
and [Scotland](../../curlobserver-learned-probe/pre-split-development-transfer/scotland-proposals.json)
intervals. Their screen denominators are respectively 19, 24, 22, and 26
candidates. These older intervals have no comparable Czech-style ambiguous
abstentions beyond Latvia S21, so the zero results show narrow failure-mode
coverage, not detector safety or recall. All recordings were previously
exposed to development. The threshold choices were made after inspecting
the Czech cases and are not an independent validation result.

These six proposals are **partial moving-stone observations**, not six
verified missed throws. The source review makes them compelling places to
improve event recall, but passage-to-stone identity, physical release,
contact outcome, full event boundaries, and complete post-event boards
remain unverified. Exact-prefix deduplication also misses near-duplicate
tracks. Keep the 79-candidate frozen screen and 91-candidate development
screen unchanged until a predeclared combined detector is evaluated on an
unseen full recording with independent exhaustive throw labels.

The [interactive review viewer with partial boards](left-bound-full-match/pre-split-board-review/index.html)
places the six prefixes and S132 duplicate beside the source video. The
[quiet-tail board audit](PRE-SPLIT-BOARD-RESULTS.md) found stable partial
observations for all six windows, but source frames show an omitted yellow
stone in S40; these boards are not complete game states.
