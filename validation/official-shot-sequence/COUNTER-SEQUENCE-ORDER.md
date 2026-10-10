# Counter-to-camera-shot order diagnostic

The [source-scoped audit](pwg2022-counter-sequence-order-development.json) checks whether an ambiguous delayed scoreboard counter can be placed between its nearest *already linked* counters in camera-shot order. It keeps options with origin probability at least 0.2 and a strictly intermediate shot number. A single surviving option is a review proposal, not an event decision. Existing links are treated as provisional anchors; no ledger is changed.

| Exposed recording | Linked-anchor reversals | Multi-option counters | Unique order proposals |
| --- | ---: | ---: | ---: |
| Switzerland 2022 | 1 | 3 | 1 |
| China 2022 | 0 | 3 | 0 |
| Slovakia 2022 | 2 | 4 | 3 |
| Canada–Norway 2022 | 0 | 1 | 0 |
| **Total** | **3** | **11** | **4** |

The four *order-only* proposals are Swiss B01 → S25 and Slovakia B61 → S286, B80 → S372, B86 → S411. B01 and B61 already appear as linked visual candidates in the later provisional union. B80 and B86 would attach counters to existing, currently unlinked visual candidates, so they do not imply two more throws. The rule abstains on Norway B69; both candidate shots fit between its linked neighbours. This is complementary to the separate timing and ice-context clues, not a substitute for physical stone identity.

**Source check of the two new Slovakia proposals:** the sampled delivery views in [the source-frame contact sheet](slovakia-b80-b86-order-review.jpg) show yellow-handled stones in S372 and S411, whereas both proposed counters B80 and B86 are red. The previously frozen [post-cut colour audit](pwg2022-visual-only-postcut-colours.json) independently records yellow motion for S411 and abstains for S372. A [reproducible colour screen](pwg2022-counter-order-colour-screen-development.json) joins these two frozen outputs by source and shot ID: B86 → S411 is flagged as a colour conflict; B80 → S372 remains unknown. **Neither counter link should be added from order alone.** The image samples are development review, not independent physical throw labels; they do not establish where either stone settles. Even matching post-cut colour would not prove that the same stone crossed the camera edit.

A subsequent [held-cap scan](slovakia-ambiguous-held-colour-development.json) applies the existing cap detector and a patch model trained without Slovakia to all 13 camera shots offered by the four ambiguous Slovakia counters. In the selected delivery-side corridor it finds a sustained **yellow** cap in S372 and S411, both conflicting with their proposed red counters. This automatically supplies the missing source-colour warning for S372. It also finds a red cap held in S373's overhead house view, where a stationary settled stone can satisfy the same rule; S373 has only 0.015 origin probability. Among all 13 shots, six have one detected held colour and seven abstain. This is a postscore corridor check chosen after seeing S372/S411. It is not a release detector or a safe way to assign the counters, and it makes no event-ledger changes. Reproduce it with `PYTHONPATH=prototype feasibility/scripts/python.sh prototype/scripts/audit_slovakia_ambiguous_held_colour.py`.

The unchanged [held-to-motion release cue](SLOVAKIA-AMBIGUOUS-RELEASE-PASSAGES.md) fires in three of those 13 shots: yellow S287, red S374, and yellow S411. It abstains on the stationary overhead S373. The local raw scoreboard readings around B80/B81 oscillate, so S374's red release cue does not establish which delayed counter belongs to it. No counter link is promoted.

Three existing linked-counter pairs reverse camera-shot order: Swiss B86/B87 and Slovakia B56/B57 and B58/B59. Those are review priorities and a warning against enforcing monotonic order across the entire ledger as if its links were ground truth. The audit does not resolve the physical throws, exact release/settle times, or full-match precision and recall. All four recordings were exposed development sources; independent validation remains pending.

Run `python prototype/scripts/audit_2022_counter_sequence_order.py` from the repository root to verify the artifact against the frozen inputs and code hashes.
Run `python prototype/scripts/screen_2022_counter_order_colour.py` to verify the source-colour screen.
