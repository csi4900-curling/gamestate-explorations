# S13 red-cap fragment at 502 s: continuation probe

The frozen [board-blind cap continuation](full-reviewed-stone-cap-continuations-development.json)
stopped S13 at 502.0 s because two red colour components satisfied its
motion gate. The [unmarked source crops and marked contact sheet](s13-fragment-contact-source/manifest.json)
show a large red-handle component and a small fragment directly above it
on the rightward-moving stone. The two detected components at 502.0 s have
areas 199.0 and 29.5 px², horizontally overlapping boxes, and vertically
touching boxes. The original selector's prediction errors were 3.061 and
12.728 px, below its required 15 px separation margin, so abstention was
consistent with its frozen rules.

The [fragment-aware development replay](full-reviewed-stone-fragment-merge-continuations-development.json)
merges only a uniquely paired small component adjacent to a larger one,
then applies the unchanged causal motion selector. It uses past path points
and the current frame; the future board position is used only for the
evaluation horizon and terminal-distance check. Across all **12** eligible
reviewed Czech gaps, the original rule reached the first same-colour board
frame in **4**, and the fragment-aware variant reached it in **5**. **Only
E011/S13 changes horizon status.** E028 also has one fragment merge but
still abstains later; the other ten cases retain their original horizon
outcome. The [unmarked E028 crop](e028-fragment-source/source-975.0-crop.png)
shows a broom crossing a red handle. The small fragment merges, but two
larger red components still compete, so the tracker correctly abstains
under the variant's own rules.

S13's selected image-cap sequence now reaches **505.0 s**, the first red
partial-board observation, ending **0.959 px** from that observation's cap
center in the 1080p image. The [contact sheet](s13-fragment-contact-source/s13-500-505-contact-sheet.jpg)
shows the selected cap on the rightward-moving red stone through the 502 s
fragment. Around 500.5–501.0 s another red stone is close enough to create
a possible contact or identity-swap point. The frames support a *local
path-to-board correspondence hypothesis*, stronger than nearest-board
matching alone, but half-second sampling and nearby same-colour stones do
not independently prove physical identity through contact or a physical
settle time.

Horizon reach alone is insufficient: E096 already reached its first
same-colour board frame in the frozen replay but ended **446.093 px** from
that board center. Other gaps still abstain. The fragment rule was devised
after inspecting this exposed S13 frame. A
[Latvia recorded-step transfer audit](../canada-latvia-2024/cap-fragment-merge-recorded-step-transfer-development.json)
finds **zero compatible fragment pairs in 95 already sampled steps across
14 candidates**. This means the merge cannot change those deterministic
Latvia paths before their original stops; it is not a fresh full-video
replay or a test on another camera family. No event F1, persistent stone ID,
complete board state, or simulation readiness follows from this pilot.

Reproduce with
`feasibility/scripts/python.sh prototype/scripts/probe_czech_fragment_aware_cap_continuation.py`
and render the source packet with
`feasibility/scripts/python.sh prototype/scripts/render_czech_s13_fragment_contact.py`
and the E028 source crop with
`feasibility/scripts/python.sh prototype/scripts/render_czech_e028_fragment_source.py`
after moving their outputs aside. The Latvia recorded-step audit is
`python prototype/scripts/audit_latvia_cap_fragment_transfer.py`. The replay
pins the source videos, reviewed-gap inventory, original continuation,
component detector, selector, and fragment-merge code by SHA-256.
